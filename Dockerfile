FROM kbase/sdkbase2:python
MAINTAINER Sean Jungbluth <sjungbluth@lbl.gov>
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# To install all the dependencies
RUN apt-get update && apt-get install -y libgsl0-dev samtools git zip unzip bedtools bowtie2 wget python-pip libjpeg-dev zlib1g-dev libbz2-dev python3-pandas

#RUN conda install --channel=numba llvmlite

# https://github.com/merenlab/anvio/issues/1637
RUN wget https://github.com/merenlab/anvio/releases/download/v7.1/anvio-7.1.tar.gz && \
    tar -xvzf anvio-7.1.tar.gz && \
    sed -i 's/pandas==0.25.1/pandas/' /anvio-7.1/requirements.txt && \
    tar -czvf anvio-7.1.tar.gz /anvio-7.1

RUN pip install --upgrade pip && \
    pip install cython numpy && \
    pip install anvio-7.1.tar.gz

WORKDIR /kb/module/lib/kb_anvio/bin/

RUN wget --no-check-certificate https://sourceforge.net/projects/bbmap/files/latest/download && tar -xvf download

RUN wget https://github.com/lh3/minimap2/releases/download/v2.17/minimap2-2.17.tar.bz2 && tar -xvf minimap2-* && cd minimap2* && make && cd ../ && rm minimap2-2.17.tar.bz2

# RUN wget ftp://ftp.ccb.jhu.edu/pub/infphilo/hisat2/downloads/hisat2-2.1.0-Linux_x86_64.zip && unzip hisat2-* && rm hisat2-2.1.0-Linux_x86_64.zip

# RUN pip install nose jinja2 coverage

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

ENV PATH=/kb/module/lib/kb_anvio/bin:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/bbmap:$PATH
ENV PATH=/kb/module/lib/kb_anvio/bin/minimap2-2.17/:$PATH
# ENV PATH=/kb/module/lib/kb_anvio/bin/hisat2-2.1.0/:$PATH
# ENV PATH=/kb/deployment/bin/ANVIO/bin:/kb/deployment/bin/ANVIO/scripts:$PATH

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
