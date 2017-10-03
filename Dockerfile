FROM buildpack-deps:stretch-curl

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clang-3.9 \
        cmake \
        gcc \
        git \
        jupyter-nbextension-jupyter-js-widgets \
        jupyter-notebook \
        libgraphviz-dev \
        make \
        pkg-config \
        python2.7 \
        python-dev \
        python-pip \
        python-setuptools \
        python-wheel \
        xz-utils

RUN mkdir /root/llvm && curl -L http://releases.llvm.org/5.0.0/llvm-5.0.0.src.tar.xz | tar -C /root/llvm -xJ --strip-components 1

RUN git clone --depth=1 https://github.com/jakubbrzeski/regallo.git /root/regallo
WORKDIR /root/regallo
RUN cp -a llvm/src/* /root/llvm/ && rm -rf llvm/src && ln -s /root/llvm llvm/src
RUN echo "add_subdirectory(CFGExtractor)" >> llvm/src/lib/Transforms/CMakeLists.txt
RUN mkdir llvm/build
WORKDIR /root/regallo/llvm/build
RUN CC=/usr/bin/clang-3.9 CXX=/usr/bin/clang++-3.9 cmake -DCMAKE_BUILD_TYPE=Release ../src && make -j2

WORKDIR /root/regallo/py-regallo
RUN pip install -r requirements.txt
CMD jupyter-notebook tutorial.ipynb
