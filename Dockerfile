FROM kbase/sdkbase2:python
MAINTAINER Sean Jungbluth <sjungbluth@lbl.gov>
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# To install all the dependencies
RUN apt-get update && apt-get install -y libgsl0-dev samtools git zip unzip bedtools bowtie2 wget python-pip libjpeg-dev zlib1g-dev libbz2-dev python3-pandas sqlite3 mcl bowtie2 bwa autoconf

# https://github.com/merenlab/anvio/issues/1637
RUN wget https://github.com/merenlab/anvio/releases/download/v7.1/anvio-7.1.tar.gz && \
    tar -xvzf anvio-7.1.tar.gz && \
    # need to use default pandas for now, fixing below
    sed -i 's/pandas==0.25.1/pandas/' /anvio-7.1/requirements.txt && \
    tar -czvf anvio-7.1.tar.gz /anvio-7.1

RUN pip install --upgrade pip && \
    pip install cython numpy && \
    pip install anvio-7.1.tar.gz

RUN pip install -U PyYAML

WORKDIR /kb/module/lib/kb_anvio/bin/

RUN wget --no-check-certificate https://sourceforge.net/projects/bbmap/files/latest/download && \
    tar -xvf download && \
    rm download

RUN wget https://github.com/lh3/minimap2/releases/download/v2.26/minimap2-2.26.tar.bz2 && \
    tar -xvf minimap2-* && \
    cd minimap2* && \
    make && \
    mv minimap2 /usr/local/bin/minimap2 && \
    cd ../ && \
    rm -rf minimap2*

RUN wget https://cloud.biohpc.swmed.edu/index.php/s/oTtGWbWjaxsQ2Ho/download && \
    unzip download && \
    cd hisat2-* && \
    mv hisat2-build /usr/local/bin/hisat2-build && \
    mv hisat2 /usr/local/bin/hisat2 && \
    cd ../ && \
    rm -rf hisat2* && \
    rm download

RUN wget https://github.com/hyattpd/Prodigal/releases/download/v2.6.3/prodigal.linux && \
    chmod +x prodigal.linux && \
    mv prodigal.linux /usr/local/bin/prodigal

RUN wget http://eddylab.org/software/hmmer/hmmer-3.3.2.tar.gz && \
    tar -xvzf hmmer-3.3.2.tar.gz && \
    cd hmmer-3.3.2 && \
    ./configure && \
    make && \
    make install && \
    cd ../ && \
    rm -rf hmmer-3*

RUN wget https://github.com/bbuchfink/diamond/releases/download/v2.1.7/diamond-linux64.tar.gz && \
    tar -xvzf diamond-linux64.tar.gz && \
    mv diamond /usr/local/bin && \
    rm -rf diamond*

RUN wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.14.0+-x64-linux.tar.gz && \
    tar -xvzf ncbi-blast-2.14.0+-x64-linux.tar.gz && \
    rm ncbi-blast-2.14.0+-x64-linux.tar.gz

RUN wget https://github.com/voutcn/megahit/releases/download/v1.2.9/MEGAHIT-1.2.9-Linux-x86_64-static.tar.gz && \
    tar zvxf MEGAHIT-1.2.9-Linux-x86_64-static.tar.gz && \
    mv MEGAHIT-1.2.9-Linux-x86_64-static/bin/megahit /usr/local/bin/megahit && \
    chmod +x /usr/local/bin/megahit && \
    rm -rf MEGAHIT*

RUN wget https://github.com/ablab/spades/releases/download/v3.15.5/SPAdes-3.15.5-Linux.tar.gz && \
    tar -xvzf SPAdes-3.15.5-Linux.tar.gz && \
    rm SPAdes-3.15.5-Linux.tar.gz

RUN wget http://trna.ucsc.edu/software/trnascan-se-2.0.9.tar.gz && \
    tar -xvzf trnascan-se-2.0.9.tar.gz && \
    cd tRNAscan-SE-2.0 && \
    ./configure && \
    make && \
    make install && \
    cd ../ && \
    rm trnascan-se-2.0.9.tar.gz && \
    rm -rf tRNAscan-SE-2.0

RUN wget http://eddylab.org/infernal/infernal-1.1.4-linux-intel-gcc.tar.gz && \
    tar -xvzf infernal-1.1.4-linux-intel-gcc.tar.gz && \
    mv /kb/module/lib/kb_anvio/bin/infernal-1.1.4-linux-intel-gcc/binaries/cmsearch /usr/local/bin/cmsearch && \
    mv /kb/module/lib/kb_anvio/bin/infernal-1.1.4-linux-intel-gcc/binaries/cmscan /usr/local/bin/cmscan

# terminal length becomes negative value in KBase console --> hardcoding wrap_width
RUN sed -i 's/wrap_width .*/wrap_width = 100/' /miniconda/lib/python3.6/site-packages/anvio/terminal.py

# removing emojis in code
RUN sed -i 's/attention and patience../attention and patience./' /miniconda/lib/python3.6/site-packages/anvio/kegg.py
RUN sed -i 's/successfully recovered../successfully recovered/' /miniconda/lib/python3.6/site-packages/anvio/kegg.py
RUN sed -i 's/{contig} ..)$/{contig} \")/' /miniconda/lib/python3.6/site-packages/anvio/kegg.py
RUN sed -i 's/ Sorry.*/ Sorry\")/' /miniconda/lib/python3.6/site-packages/anvio/kegg.py

# fix the thing we did above during anvio install
RUN pip install pandas==0.25.1

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

ENV PATH=/kb/module/lib/kb_anvio/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/bbmap:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/ncbi-blast-2.14.0+/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/SPAdes-3.15.5-Linux/bin:$PATH

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
