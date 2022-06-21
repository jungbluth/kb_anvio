# -*- coding: utf-8 -*-
import os
import time
import shutil
import unittest
from configparser import ConfigParser

from kb_anvio.kb_anvioImpl import kb_anvio
from kb_anvio.kb_anvioServer import MethodContext
from kb_anvio.authclient import KBaseAuth as KBaseAuth

from kb_anvio.Utils.AnvioUtil import AnvioUtil


from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.WorkspaceClient import Workspace


class kb_anvioTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # token = os.environ.get('KB_AUTH_TOKEN', None)
        cls.token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_anvio'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(cls.token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_anvio',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = kb_anvio(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_kb_anvio_" + str(suffix)
        # ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa

        cls.ws_info = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.ru = ReadsUtils(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.au = AssemblyUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.anvio_runner = AnvioUtil(cls.cfg)
        cls.prepare_data()


    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa

    @classmethod
    def prepare_data(cls):
        """
        Lets put everything on workspace
        """
        #
        # READS 1
        # building Interleaved library
        pe1_reads_filename = 'lib1.oldstyle.fastq'
        pe1_reads_path = os.path.join(cls.scratch, pe1_reads_filename)

        # gets put on scratch. "work/tmp" is scratch
        shutil.copy(os.path.join("data", pe1_reads_filename), pe1_reads_path)

        int1_reads_params = {
            'fwd_file': pe1_reads_path,
            'sequencing_tech': 'Unknown',
            'wsname': cls.ws_info[1],
            'name': 'MyInterleavedLibrary1',
            'interleaved': 'true'
        }

        #from scratch upload to workspace

        cls.int1_oldstyle_reads_ref = cls.ru.upload_reads(int1_reads_params)['obj_ref']
        print("cls.int1_oldstyle_reads_ref***")
        print(str(cls.int1_oldstyle_reads_ref))

        # READS 2
        # building Interleaved library
        pe2_reads_filename = 'lib2.oldstyle.fastq'
        pe2_reads_path = os.path.join(cls.scratch, pe2_reads_filename)

        # gets put on scratch. "work/tmp" is scratch
        shutil.copy(os.path.join("data", pe2_reads_filename), pe2_reads_path)

        int2_reads_params = {
            'fwd_file': pe2_reads_path,
            'sequencing_tech': 'Unknown',
            'wsname': cls.ws_info[1],
            'name': 'MyInterleavedLibrary2',
            'interleaved': 'true'
        }

        #from scratch upload to workspace
        cls.int2_oldstyle_reads_ref = cls.ru.upload_reads(int2_reads_params)['obj_ref']


        #
        # building Assembly
        #
        assembly_filename1 = 'small_arctic_assembly.fa'
        cls.assembly_filename_path1 = os.path.join(cls.scratch, assembly_filename1)
        shutil.copy(os.path.join("data", assembly_filename1), cls.assembly_filename_path1)

        # from scratch upload to workspace
        assembly_params1 = {
            'file': {'path': cls.assembly_filename_path1},
            'workspace_name': cls.ws_info[1],
            'assembly_name': 'MyAssembly1'
        }

        # puts assembly object onto shock
        cls.assembly_ref1 = cls.au.save_assembly_from_fasta(assembly_params1)

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        return self.ws_info[1]

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    # def test_bad_run_anvio_params(self):
    #     method_name = 'test_bad_run_anvio_params'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     invalidate_input_params = {
    #       'missing_assembly_ref': 'assembly_ref1',
    #       'binned_contig_name': 'binned_contig_name',
    #       'workspace_name': 'workspace_name',
    #       'reads_list': 'reads_list',
    #       'read_mapping_tool': 'read_mapping_tool'
    #     }
    #     with self.assertRaisesRegex(
    #                 ValueError, '"assembly_ref" parameter is required, but missing'):
    #         self.getImpl().run_kb_anvio(self.getContext(), invalidate_input_params)

    #     invalidate_input_params = {
    #       'assembly_ref': 'assembly_ref1',
    #       'missing_binned_contig_name': 'binned_contig_name',
    #       'workspace_name': 'workspace_name',
    #       'reads_list': 'reads_list',
    #       'read_mapping_tool': 'read_mapping_tool'
    #     }
    #     with self.assertRaisesRegex(
    #                 ValueError, '"binned_contig_name" parameter is required, but missing'):
    #         self.getImpl().run_kb_anvio(self.getContext(), invalidate_input_params)

    #     invalidate_input_params = {
    #       'assembly_ref': 'assembly_ref1',
    #       'binned_contig_name': 'binned_contig_name',
    #       'missing_workspace_name': 'workspace_name',
    #       'reads_list': 'reads_list',
    #       'read_mapping_tool': 'read_mapping_tool'
    #     }
    #     with self.assertRaisesRegex(
    #                 ValueError, '"workspace_name" parameter is required, but missing'):
    #         self.getImpl().run_kb_anvio(self.getContext(), invalidate_input_params)

    #     invalidate_input_params = {
    #       'assembly_ref': 'assembly_ref1',
    #       'binned_contig_name': 'binned_contig_name',
    #       'workspace_name': 'workspace_name',
    #       'missing_reads_list': 'reads_list',
    #       'read_mapping_tool': 'read_mapping_tool'
    #     }
    #     with self.assertRaisesRegex(
    #                 ValueError, '"reads_list" parameter is required, but missing'):
    #         self.getImpl().run_kb_anvio(self.getContext(), invalidate_input_params)

    #     invalidate_input_params = {
    #       'assembly_ref': 'assembly_ref1',
    #       'binned_contig_name': 'binned_contig_name',
    #       'workspace_name': 'workspace_name',
    #       'reads_list': 'reads_list',
    #       'missing_read_mapping_tool': 'read_mapping_tool'
    #     }
    #     with self.assertRaisesRegex(
    #                 ValueError, '"read_mapping_tool" parameter is required, but missing'):
    #         self.getImpl().run_kb_anvio(self.getContext(), invalidate_input_params)


    def test_run_anvio_multiple_read_input_test1(self):
        method_name = 'test_run_anvio_multiple_read_input_test1'
        print ("\n=================================================================")
        print ("RUNNING "+method_name+"()")
        print ("=================================================================\n")
        # anvio should run to completion here
        ret = self.getImpl().run_kb_anvio(self.getContext(),
                                            {'workspace_name': self.getWsName(),
                                             'assembly_ref': self.assembly_ref1,
                                             'read_mapping_tool': 'bbmap_default',
                                             'min_contig_length': 3000,
                                             'contig_split_size': 20000,
                                             'kmer_size': 4,
                                            # 'reads_list': [self.int1_oldstyle_reads_ref, self.int2_oldstyle_reads_ref] })
                                             'reads_list': [self.int1_oldstyle_reads_ref] })


    # def test_run_anvio_bbmap_default(self):
    #     method_name = 'test_run_anvio_bbmap_default'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'bbmap_default',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })


    # def test_run_anvio_bbmap_fast(self):
    #     method_name = 'test_run_anvio_bbmap_fast'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'bbmap_fast',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })


    # def test_run_anvio_bbmap_very_sensitive(self):
    #     method_name = 'test_run_anvio_bbmap_very_sensitive'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'bbmap_very_sensitive',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })

    # def test_run_anvio_bowtie2_default(self):
    #     method_name = 'test_run_anvio_bowtie2_default'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'bowtie2_default',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })

    # def test_run_anvio_bowtie2_very_sensitive(self):
    #     method_name = 'test_run_anvio_bowtie2_very_sensitive'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'bowtie2_very_sensitive',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })

    # def test_run_anvio_minimap2(self):
    #     method_name = 'test_run_anvio_minimap2'
    #     print ("\n=================================================================")
    #     print ("RUNNING "+method_name+"()")
    #     print ("=================================================================\n")

    #     # anvio should run to completion here
    #     ret = self.getImpl().run_kb_anvio(self.getContext(),
    #                                         {'workspace_name': self.getWsName(),
    #                                          'assembly_ref': self.assembly_ref1,
    #                                          'read_mapping_tool': 'minimap2',
    #                                          'min_contig_length': 3000,
    #                                          'contig_split_size': 10000,
    #                                          'contig_split_overlap': 0,
    #                                          'kmer_size': 4,
    #                                          'max_clusters_for_vgmm': 400,
    #                                          'max_iterations_for_vgmm': 500,
    #                                          'total_percentage_pca': 90,
    #                                          'no_cov_normalization': '--no_cov_normalization',
    #                                          'no_total_coverage': '--no_total_coverage',
    #                                          'binned_contig_name': 'anvio_bin_obj',
    #                                          'reads_list': [self.int1_oldstyle_reads_ref] })
    #     self._test_bc_headers(ret)

    # def _test_bc_headers(self, ret):

    #     bc_upa = ret[0]['binned_contig_obj_ref']

    #     bc_objData = self.dfu.get_objects({
    #         'object_refs': [bc_upa]
    #         })['data'][0]['data']

    #     assembly_objData = self.dfu.get_objects({
    #         'object_refs': [bc_objData['assembly_ref']]
    #         })['data'][0]['data']


    #     bc_header_l = sum([list(bin['contigs'].keys()) for bin in bc_objData['bins']], [])
    #     assembly_header_l = list(assembly_objData['contigs'].keys())

    #     assert len(bc_header_l) > 0 and len(assembly_header_l) > 0

    #     print('Sampling headers ...', bc_header_l[0], assembly_header_l[0])

    #     bc_header_set = set(bc_header_l)
    #     assembly_header_set = set(assembly_header_l)

    #     if len(bc_header_set) < len(bc_header_l):
    #         print('Warning: BinnedContigs headers not unique')
    #     if len(assembly_header_set) < len(assembly_header_l):
    #         print('Warning: Assembly headers not unique')

    #     assert bc_header_set.issubset(assembly_header_set)
