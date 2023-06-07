import errno
import json
import os
import subprocess
import sys
import time
import uuid
import zipfile
import copy
import glob
import shutil

from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.MetagenomeUtilsClient import MetagenomeUtils
from installed_clients.ReadsUtilsClient import ReadsUtils
# from installed_clients.KBParallelClient import KBParallel

from random import seed
from random import randint
# seed random number generator
seed(1)


def log(message, prefix_newline=False):
    """Logging function, provides a hook to suppress or redirect log messages."""
    print(('\n' if prefix_newline else '') + '{0:.2f}'.format(time.time()) + ': ' + str(message))


class AnvioUtil:
    # ANVIO_BASE_PATH = '/kb/deployment/bin/ANVIO'
    ANVIO_RESULT_DIRECTORY = 'anvio_output_dir'
    BINNER_BIN_RESULT_DIR = 'final_bins'
    MAPPING_THREADS = 4
    BBMAP_MEM = '30g'

    def __init__(self, config):
        self.callback_url = config['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        self.shock_url = config['shock-url']
        self.ws_url = config['workspace-url']
        self.dfu = DataFileUtil(self.callback_url)
        self.ru = ReadsUtils(self.callback_url)
        self.au = AssemblyUtil(self.callback_url)
        self.mgu = MetagenomeUtils(self.callback_url)

    def _validate_run_anvio_params(self, task_params):
        """
        _validate_run_anvio_params:
                validates params passed to run_anvio method
        """
        log('Start validating run_anvio params')

        # check for required parameters
        for p in ['assembly_ref', 'workspace_name', 'reads_list', 'read_mapping_tool', 'kmer_size', 'contig_split_size', 'min_contig_length']:
            if p not in task_params:
                raise ValueError('"{}" parameter is required, but missing'.format(p))

    def _mkdir_p(self, path):
        """
        _mkdir_p: make directory for given path
        """
        if not path:
            return
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def _run_command(self, command):
        """
        _run_command: run command and print result
        """
        os.chdir(self.scratch)
        log('Start executing command:\n{}'.format(command))
        log('Command is running from:\n{}'.format(self.scratch))
        pipe = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        output, stderr = pipe.communicate()
        exitCode = pipe.returncode

        if (exitCode == 0):
            log('Executed command:\n{}\n'.format(command) +
                'Exit Code: {}\n'.format(exitCode))
        else:
            error_msg = 'Error running command:\n{}\n'.format(command)
            error_msg += 'Exit Code: {}\nOutput:\n{}\nStderr:\n{}'.format(exitCode, output, stderr)
            raise ValueError(error_msg)
            sys.exit(1)
        return (output, stderr)

    # this function has been customized to return read_type variable (interleaved vs single-end library)
    def stage_reads_list_file(self, reads_list):
        """
        stage_reads_list_file: download fastq file associated to reads to scratch area
                          and return result_file_path
        """

        log('Processing reads object list: {}'.format(reads_list))

        result_file_path = []
        read_type = []

        # getting from workspace and writing to scratch. The 'reads' dictionary now has file paths to scratch.
        reads = self.ru.download_reads({'read_libraries': reads_list, 'interleaved': None})['files']

        # reads_list is the list of file paths on workspace? (i.e. 12804/1/1).
        # "reads" is the hash of hashes where key is "12804/1/1" or in this case, read_obj and
        # "files" is the secondary key. The tertiary keys are "fwd" and "rev", as well as others.
        for read_obj in reads_list:
            files = reads[read_obj]['files']    # 'files' is dictionary where 'fwd' is key of file path on scratch.
            result_file_path.append(files['fwd'])
            read_type.append(files['type'])
            if 'rev' in files and files['rev'] is not None:
                result_file_path.append(files['rev'])

        return result_file_path, read_type

    def _get_contig_file(self, assembly_ref):
        """
        _get_contig_file: get contig file from GenomeAssembly object
        """
        contig_file = self.au.get_assembly_as_fasta({'ref': assembly_ref}).get('path')

        sys.stdout.flush()
        contig_file = self.dfu.unpack_file({'file_path': contig_file})['file_path']

        return contig_file

    def run_anvi_script_reformat_fasta(self, task_params):
        min_contig_length = task_params['min_contig_length']
        contig_file_path = task_params['contig_file_path']

        clean_contig_file_path = task_params['contig_file_path'] + "_anvio-reformatted"
        command = 'anvi-script-reformat-fasta '
        command += '{} '.format(contig_file_path)
        command += '-o {} '.format(clean_contig_file_path)
        command += '-l {} '.format(min_contig_length)
        command += '--simplify-names'

        log('running anvi_script_reformat_fasta: {}'.format(command))
        self._run_command(command)
        return clean_contig_file_path

    def run_anvi_gen_contigs_database(self, task_params):
        min_contig_length = task_params['min_contig_length']
        contig_file_path = task_params['contig_file_path']
        contig_split_size = task_params['contig_split_size']
        kmer_size = task_params['kmer_size']

        clean_contig_file_path = task_params['contig_file_path'] + "_anvio-reformatted"
        command = 'anvi-gen-contigs-database '
        command += '-f {} '.format(contig_file_path)
        command += '-o contigs.db '
        command += '--split-length {} '.format(contig_split_size)
        command += '--kmer-size {} '.format(kmer_size)
        command += '-T 10 '
        command += '--prodigal-translation-table 11 '
        command += '-n "{} contig database"'.format(contig_file_path.split("/")[-1])

        log('running anvi_gen_contigs_database: {}'.format(command))
        self._run_command(command)

    def deinterlace_raw_reads(self, fastq):
        fastq_forward = fastq.split('.fastq')[0] + "_forward.fastq"
        fastq_reverse = fastq.split('.fastq')[0] + "_reverse.fastq"
        command = 'deinterleave_fastq.sh < {} {} {}'.format(fastq, fastq_forward, fastq_reverse)
        try:
            self._run_command(command)
        except Exception:
            raise Exception("Cannot deinterlace fastq file!")
        return (fastq_forward, fastq_reverse)

    def run_read_mapping_interleaved_pairs_mode(self, task_params, assembly_clean, fastq, sam):
        read_mapping_tool = task_params['read_mapping_tool']
        log("running {} mapping in interleaved mode.".format(read_mapping_tool))
        random_seed_int = randint(0, 999999999)
        log("randomly selected seed (integer) used for read mapping is: {}".format(random_seed_int))
        if task_params['read_mapping_tool'] == 'bbmap_fast':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'fast interleaved=true mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bbmap_default':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'interleaved=true mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bbmap_very_sensitive':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'vslow=true '
            command += 'interleaved=true mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bowtie2_default':
            (fastq_forward, fastq_reverse) = self.deinterlace_raw_reads(fastq)
            bt2index = os.path.basename(assembly_clean) + '.bt2'
            command = 'bowtie2-build -f {} '.format(assembly_clean)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} && '.format(bt2index)
            command += 'bowtie2 -x {} '.format(bt2index)
            command += '-1 {} '.format(fastq_forward)
            command += '-2 {} '.format(fastq_reverse)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '-S {}'.format(sam)
        elif task_params['read_mapping_tool'] == 'bowtie2_very_sensitive':
            (fastq_forward, fastq_reverse) = self.deinterlace_raw_reads(fastq)
            bt2index = os.path.basename(assembly_clean) + '.bt2'
            command = 'bowtie2-build -f {} '.format(assembly_clean)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} && '.format(bt2index)
            command += 'bowtie2 --very-sensitive -x {} '.format(bt2index)
            command += '-1 {} '.format(fastq_forward)
            command += '-2 {} '.format(fastq_reverse)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '-S {}'.format(sam)
        elif task_params['read_mapping_tool'] == 'minimap2':
            (fastq_forward, fastq_reverse) = self.deinterlace_raw_reads(fastq)
            command = 'minimap2 -ax sr -t {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} '.format(assembly_clean)
            command += '{} '.format(fastq_forward)
            command += '{} > '.format(fastq_reverse)
            command += '{}'.format(sam)
        elif task_params['read_mapping_tool'] == 'hisat2':
            (fastq_forward, fastq_reverse) = self.deinterlace_raw_reads(fastq)
            ht2index = os.path.basename(assembly_clean) + '.ht2'
            command = 'hisat2-build {} '.format(assembly_clean)
            command += '{} && '.format(ht2index)
            command += 'hisat2 -x {} '.format(ht2index)
            command += '-1 {} '.format(fastq_forward)
            command += '-2 {} '.format(fastq_reverse)
            command += '-S {} '.format(sam)
            command += '--seed {} '.format(random_seed_int)
            command += '--threads {}'.format(self.MAPPING_THREADS)
        log('running alignment command: {}'.format(command))
        out, err = self._run_command(command)

    def run_read_mapping_unpaired_mode(self, task_params, assembly_clean, fastq, sam):
        read_mapping_tool = task_params['read_mapping_tool']
        log("running {} mapping in single-end (unpaired) mode.".format(read_mapping_tool))
        random_seed_int = randint(0, 999999999)
        log("randomly selected seed (integer) used for read mapping is: {}".format(random_seed_int))
        if task_params['read_mapping_tool'] == 'bbmap_fast':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'fast interleaved=false mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bbmap_default':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'interleaved=false mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bbmap_very_sensitive':
            log("Warning: bbmap does not support setting random seeds, so results are not reproducible.")
            command = 'bbmap.sh -Xmx{} '.format(self.BBMAP_MEM)
            command += 'threads={} '.format(self.MAPPING_THREADS)
            command += 'ref={} '.format(assembly_clean)
            command += 'in={} '.format(fastq)
            command += 'out={} '.format(sam)
            command += 'vslow=true '
            command += 'interleaved=false mappedonly nodisk overwrite'
        elif task_params['read_mapping_tool'] == 'bowtie2_default':
            bt2index = os.path.basename(assembly_clean) + '.bt2'
            command = 'bowtie2-build -f {} '.format(assembly_clean)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} && '.format(bt2index)
            command += 'bowtie2 -x {} '.format(bt2index)
            command += '-U {} '.format(fastq)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '-S {}'.format(sam)
        elif task_params['read_mapping_tool'] == 'bowtie2_very_sensitive':
            bt2index = os.path.basename(assembly_clean) + '.bt2'
            command = 'bowtie2-build -f {} '.format(assembly_clean)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} && '.format(bt2index)
            command += 'bowtie2 --very-sensitive -x {} '.format(bt2index)
            command += '-U {} '.format(fastq)
            command += '--threads {} '.format(self.MAPPING_THREADS)
            command += '-S {}'.format(sam)
        elif task_params['read_mapping_tool'] == 'minimap2':
            command = 'minimap2 -ax sr -t {} '.format(self.MAPPING_THREADS)
            command += '--seed {} '.format(random_seed_int)
            command += '{} '.format(assembly_clean)
            command += '{} > '.format(fastq)
            command += '{}'.format(sam)
        elif task_params['read_mapping_tool'] == 'hisat2':
            ht2index = os.path.basename(assembly_clean) + '.ht2'
            command = 'hisat2-build {} '.format(assembly_clean)
            command += '{} && '.format(ht2index)
            command += 'hisat2 -x {} '.format(ht2index)
            command += '-U {} '.format(fastq)
            command += '-S {} '.format(sam)
            command += '--seed {} '.format(random_seed_int)
            command += '--threads {}'.format(self.MAPPING_THREADS)
        log('running alignment command: {}'.format(command))
        out, err = self._run_command(command)

    def convert_sam_to_sorted_and_indexed_bam(self, sam):
        # create bam files from sam files
        sorted_bam = os.path.abspath(sam).split('.sam')[0] + "_sorted.bam"

        command = 'samtools view -F 0x04 -uS {} | '.format(sam)
        command += 'samtools sort - -o {}'.format(sorted_bam)

        log('running samtools command to generate sorted bam: {}'.format(command))
        self._run_command(command)

        # verify we got bams
        if not os.path.exists(sorted_bam):
            log('Failed to find bam file\n{}'.format(sorted_bam))
            sys.exit(1)
        elif(os.stat(sorted_bam).st_size == 0):
            log('Bam file is empty\n{}'.format(sorted_bam))
            sys.exit(1)

        # index the bam file
        command = 'samtools index {}'.format(sorted_bam)

        log('running samtools command to index sorted bam: {}'.format(command))
        self._run_command(command)

        return sorted_bam

    def run_anvi_init_bam(self, sorted_bam):
        sorted_raw_bam = sorted_bam + "-RAW.bam"
        command = 'anvi-init-bam '
        command += '{} '.format(sorted_bam)
        command += '-o {} '.format(sorted_raw_bam)
        command += '-T 10 '

        log('running anvi_init_bam: {}'.format(command))
        self._run_command(command)
        return sorted_raw_bam

    def run_anvi_profile(self, raw_sorted_bam):
        command = 'anvi-profile '
        command += '-i {} '.format(raw_sorted_bam)
        command += '-c contigs.db '
        command += '-T 10 '

        log('running anvi-profile: {}'.format(command))
        self._run_command(command)

    def generate_alignment_bams_and_prep_for_anvio(self, task_params, assembly_clean):
        """
            This function runs the selected read mapper and creates the
            sorted and indexed bam files from sam files using samtools.
        """

        reads_list = task_params['reads_list']

        (read_scratch_path, read_type) = self.stage_reads_list_file(reads_list)

        sorted_bam_file_list = []

        # list of reads files, can be 1 or more. assuming reads are either type unpaired or interleaved
        # will not handle unpaired forward and reverse reads input as seperate (non-interleaved) files

        for i in range(len(read_scratch_path)):
            fastq = read_scratch_path[i]
            fastq_type = read_type[i]

            sam = os.path.basename(fastq).split('.fastq')[0] + ".sam"
            # sam = os.path.join(self.ANVIO_RESULT_DIRECTORY, sam)

            if fastq_type == 'interleaved':  # make sure working - needs tests
                log("Running interleaved read mapping mode")
                self.run_read_mapping_interleaved_pairs_mode(task_params, assembly_clean, fastq, sam)
            else:  # running read mapping in single-end mode
                log("Running unpaired read mapping mode")
                self.run_read_mapping_unpaired_mode(task_params, assembly_clean, fastq, sam)

            sorted_bam = self.convert_sam_to_sorted_and_indexed_bam(sam)

            sorted_bam_file_list.append(sorted_bam)

            raw_sorted_bam = self.run_anvi_init_bam(sorted_bam)

            self.run_anvi_profile(raw_sorted_bam)

        if len(task_params['reads_list']) > 1:
            self.run_anvi_merge(task_params)

        return sorted_bam_file_list

    def run_anvi_merge(self, task_params):
        command = 'anvi-merge '
        command += '*/PROFILE.db '
        command += '-o SAMPLES-MERGED '
        command += '-c contigs.db '
        command += '--enforce-hierarchical-clustering'

        log('running run_anvi_merge: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_hmms(self):
        command = 'anvi-run-hmms '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--quiet '.format(self.MAPPING_THREADS)
        log('running anvi_run_hmms: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_ncbi_cog(self):
        command = 'anvi-run-ncbi-cogs '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--sensitive '
        command += '--cog-data-dir /data/anviodb/COG'
        log('running anvi_run_ncbi_cog: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_pfams(self):
        command = 'anvi-run-pfams '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--pfam-data-dir /data/anviodb/Pfam'
        log('running anvi_run_pfams: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_kegg_kofams(self):
        command = 'anvi-run-kegg-kofams '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--kegg-data-dir /data/anviodb/KEGG'
        log('running anvi_run_kegg_kofams: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_interacdome(self):
        command = 'anvi-run-interacdome '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--interacdome-dataset representable '
        command += '-m 0.200000 '
        command += '-f 0.5 '
        command += '--interacdome-data-dir /data/anviodb/Interacdome'
        log('running anvi-run-interacdome: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_scg_taxonomy(self):
        command = 'anvi-setup-scg-taxonomy -T 1 && '
        command += 'anvi-run-scg-taxonomy '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '-P 1 '
        command += '--max-num-target-sequences 20 '
        command += '--min-percent-identity 90.0 '
        log('running anvi-run-scg-taxonomy: {}'.format(command))
        self._run_command(command)

    def run_anvi_scan_trnas(self):
        command = 'anvi-scan-trnas '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--trna-cutoff-score 20'
        log('running anvi-scan-trnas: {}'.format(command))
        self._run_command(command)

    def run_anvi_run_trna_taxonomy(self):
        command = 'anvi-run-trna-taxonomy '
        command += '-c contigs.db '
        command += '--num-threads {} '.format(self.MAPPING_THREADS)
        command += '--min-percent-identity 90.0 '
        command += '--max-num-target-sequences 100 '
        command += '-P 1'
        log('running anvi-run-trna-taxonomy: {}'.format(command))
        self._run_command(command)

    def generate_dummy_anvio_profile(self):
        command = 'anvi-profile '
        command += '-c contigs.db '
        command += '--blank-profile '
        command += '-o BLANK-PROFILE/ '
        command += '-S BLANK'
        log('running anvi-profile: {}'.format(command))
        self._run_command(command)

    def generate_output_file_list(self, result_directory):
        """
        generate_output_file_list: zip result files and generate file_links for report
        """
        log('Start packing result files')
        output_files = list()

        output_directory = os.path.join(self.scratch, str(uuid.uuid4()))
        self._mkdir_p(output_directory)
        result_file = os.path.join(output_directory, 'anvio_result.zip')

        with zipfile.ZipFile(result_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:

            for dirname, subdirs, files in os.walk(result_directory):
                for file in files:
                    # if (file.endswith('.sam') or
                    #     file.endswith('.bam') or
                    #     file.endswith('.bai') or
                    #    file.endswith('.summary')):
                    #         continue
                    # if (dirname.endswith(self.BINNER_BIN_RESULT_DIR)):
                    #         continue
                    zip_file.write(os.path.join(dirname, file), file)
                if (dirname.endswith(self.BINNER_BIN_RESULT_DIR)):
                    baseDir = os.path.basename(dirname)
                    for file in files:
                        full = os.path.join(dirname, file)
                        zip_file.write(full, os.path.join(baseDir, file))

        output_files.append({'path': result_file,
                             'name': os.path.basename(result_file),
                             'label': os.path.basename(result_file),
                             'description': 'Files generated by ANVIO App'})

        return output_files

    def generate_html_report(self, result_directory, assembly_ref):
        """
        generate_html_report: generate html summary report
        """

        log('Start generating html report')
        html_report = list()

        output_directory = os.path.join(self.scratch, str(uuid.uuid4()))
        self._mkdir_p(output_directory)
        result_file_path = os.path.join(output_directory, 'report.html')

        # get summary data from existing assembly object and bins_objects
        Summary_Table_Content = ''
        Overview_Content = ''
        # (binned_contig_count, input_contig_count, total_bins_count) = \
        #     self.generate_overview_info(assembly_ref, binned_contig_obj_ref, result_directory)

        # Overview_Content += '<p>Binned contigs: {}</p>'.format(binned_contig_count)
        # Overview_Content += '<p>Input contigs: {}</p>'.format(input_contig_count)
        # Overview_Content += '<p>Number of bins: {}</p>'.format(total_bins_count)

        with open(result_file_path, 'w') as result_file:
            with open(os.path.join(os.path.dirname(__file__), 'report_template.html'),
                      'r') as report_template_file:
                report_template = report_template_file.read()
                report_template = report_template.replace('<p>Overview_Content</p>',
                                                          Overview_Content)
                report_template = report_template.replace('Summary_Table_Content',
                                                          Summary_Table_Content)
                result_file.write(report_template)

        html_report.append({'path': result_file_path,
                            'name': os.path.basename(result_file_path),
                            'label': os.path.basename(result_file_path),
                            'description': 'HTML summary report for kb_anvio App'})
        return html_report

    def move_files_to_output_folder(self, task_params):
        shutil.move(os.path.join(self.scratch, "contigs.db"), os.path.join(self.scratch, "anvio_output_dir"))
        shutil.move(os.path.join(self.scratch, task_params['contig_file_path']), os.path.join(self.scratch, "anvio_output_dir"))
        if len(task_params['reads_list']) > 1:
            shutil.move(os.path.join(self.scratch, "SAMPLES-MERGED"), os.path.join(self.scratch, "anvio_output_dir"))
        elif len(task_params['reads_list']) == 1:
            shutil.move(glob.glob(os.path.join(self.scratch,'*_RAW'))[0], os.path.join(self.scratch, "anvio_output_dir"))
        else:
            shutil.move(os.path.join(self.scratch, "BLANK-PROFILE"), os.path.join(self.scratch, "anvio_output_dir"))

    def generate_report(self, task_params):
        """
        generate_report: generate summary report
        """
        log('Generating report')

        result_directory = os.path.join(self.scratch, "anvio_output_dir")

        task_params['result_directory'] = result_directory

        self.move_files_to_output_folder(task_params)

        output_files = self.generate_output_file_list(task_params['result_directory'])

        output_html_files = self.generate_html_report(task_params['result_directory'],
                                                      task_params['assembly_ref'])

        report_params = {
            'message': '',
            'workspace_name': task_params['workspace_name'],
            'file_links': output_files,
            'html_links': output_html_files,
            'direct_html_link_index': 0,
            'html_window_height': 266,
            'report_object_name': 'kb_anvio_report_' + str(uuid.uuid4())
        }

        kbase_report_client = KBaseReport(self.callback_url)
        output = kbase_report_client.create_extended_report(report_params)

        report_output = {'report_name': output['name'], 'report_ref': output['ref']}

        return report_output

    def run_anvio(self, task_params):
        """
        run_anvio: anvio app

        required params:
            assembly_ref: Metagenome assembly object reference
            workspace_name: the name of the workspace it gets saved to.
            reads_list: list of reads object (PairedEndLibrary/SingleEndLibrary)
            for input to anvio

        optional params:
            min_contig_length: minimum contig length; default 1000

        """
        log('--->\nrunning AnvioUtil.run_anvio\n' +
            'task_params:\n{}'.format(json.dumps(task_params, indent=1)))

        self._validate_run_anvio_params(task_params)

        # get assembly
        contig_file = self._get_contig_file(task_params['assembly_ref'])
        task_params['contig_file_path'] = contig_file

        # prep result directory
        result_directory = os.path.join(self.scratch, self.ANVIO_RESULT_DIRECTORY)
        self._mkdir_p(result_directory)

        cwd = os.getcwd()
        log('changing working dir to {}'.format(result_directory))
        os.chdir(result_directory)

        assembly_reformatted = self.run_anvi_script_reformat_fasta(task_params)
        task_params['contig_file_path'] = assembly_reformatted

        self.run_anvi_gen_contigs_database(task_params)

        self.run_anvi_run_hmms()

        self.run_anvi_run_ncbi_cog()

        self.run_anvi_run_pfams()

        # self.run_anvi_run_kegg_kofams()

        # self.run_anvi_run_interacdome()

        self.run_anvi_run_scg_taxonomy()

        # self.run_anvi_scan_trnas()

        # self.run_anvi_run_trna_taxonomy()

        # get reads
        if task_params['reads_list']:
            (reads_list_file, read_type) = self.stage_reads_list_file(task_params['reads_list'])
            task_params['read_type'] = read_type
            task_params['reads_list_file'] = reads_list_file
            self.generate_alignment_bams_and_prep_for_anvio(task_params, assembly_reformatted)
        else:
            self.generate_dummy_anvio_profile()

        # file handling and management
        os.chdir(cwd)
        log('changing working dir to {}'.format(cwd))

        log('Saved result files to: {}'.format(result_directory))
        log('Generated files:\n{}'.format('\n'.join(os.listdir(result_directory))))

        reportVal = self.generate_report(task_params)
        returnVal = {
            'result_directory': result_directory,
        }
        returnVal.update(reportVal)

        return returnVal
