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

RUN wget --no-check-certificate https://sourceforge.net/projects/bbmap/files/latest/download && tar -xvf download

RUN wget https://github.com/lh3/minimap2/releases/download/v2.17/minimap2-2.17.tar.bz2 && tar -xvf minimap2-* && cd minimap2* && make && cd ../ && rm minimap2-2.17.tar.bz2

RUN wget ftp://ftp.ccb.jhu.edu/pub/infphilo/hisat2/downloads/hisat2-2.1.0-Linux_x86_64.zip && unzip hisat2-* && rm hisat2-2.1.0-Linux_x86_64.zip

RUN wget https://github.com/hyattpd/Prodigal/releases/download/v2.6.3/prodigal.linux && \
    chmod +x prodigal.linux && \
    mv prodigal.linux /usr/local/bin/prodigal

RUN wget http://eddylab.org/software/hmmer/hmmer-3.3.2.tar.gz && \
    tar -xvzf hmmer-3.3.2.tar.gz && \
    cd hmmer-3.3.2 && \
    ./configure && \
    make && \
    make install

RUN wget https://github.com/bbuchfink/diamond/releases/download/v2.0.15/diamond-linux64.tar.gz && \
    tar -xvzf diamond-linux64.tar.gz && \
    mv diamond /usr/local/bin && \
    rm diamond-linux64.tar.gz

RUN wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.13.0+-x64-linux.tar.gz && \
    tar -xvzf ncbi-blast-2.13.0+-x64-linux.tar.gz

RUN wget https://github.com/voutcn/megahit/releases/download/v1.2.9/MEGAHIT-1.2.9-Linux-x86_64-static.tar.gz && \
    tar zvxf MEGAHIT-1.2.9-Linux-x86_64-static.tar.gz && \
    cp MEGAHIT-1.2.9-Linux-x86_64-static/bin/megahit /usr/local/bin && \
    chmod +x /usr/local/bin/megahit

RUN wget https://github.com/ablab/spades/releases/download/v3.15.4/SPAdes-3.15.4-Linux.tar.gz && \
    tar -xvzf SPAdes-3.15.4-Linux.tar.gz

RUN wget http://trna.ucsc.edu/software/trnascan-se-2.0.9.tar.gz && \
    tar -xvzf trnascan-se-2.0.9.tar.gz && \
    cd tRNAscan-SE-2.0 && \
    ./configure && \
    make && \
    make install

RUN wget http://eddylab.org/infernal/infernal-1.1.4-linux-intel-gcc.tar.gz && \
    tar -xvzf infernal-1.1.4-linux-intel-gcc.tar.gz && \
    cp /kb/module/lib/kb_anvio/bin/infernal-1.1.4-linux-intel-gcc/binaries/cmsearch /usr/local/bin/cmsearch && \
    cp /kb/module/lib/kb_anvio/bin/infernal-1.1.4-linux-intel-gcc/binaries/cmscan /usr/local/bin/cmscan

# terminal length becomes negative value in KBase console --> hardcoding wrap_width
RUN sed -i 's/wrap_width .*/wrap_width = 100/' /miniconda/lib/python3.6/site-packages/anvio/terminal.py

# protip: don't put emojis in your code
#RUN sed -i 's/attention and patience../attention and patience./' /miniconda/lib/python3.6/site-packages/anvio/kegg.py

RUN cd /miniconda/lib/python3.6/site-packages/anvio && \
    for file in *.py; do iconv -f utf-8 -t utf-8 -c $file > tmp; mv tmp $file; done
    #cd /miniconda/bin && \
    #for file in anvi*; do iconv -f utf-8 -t utf-8 -c $file > tmp; mv tmp $file; done 

# fix the thing we did above during anvio install
RUN pip install pandas==0.25.1

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

ENV PATH=/kb/module/lib/kb_anvio/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/bbmap:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/minimap2-2.17/:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/ncbi-blast-2.13.0+/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/SPAdes-3.15.4-Linux/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/hisat2-2.1.0:$PATH

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
