#!/usr/bin/env bash
export CUDA_INC_DIR=/usr/local/cuda
export CUDA_HOME=/usr/local/cuda
export LD_LIBRARY_PATH=:/usr/local/cuda/lib64:/usr/lib/cuda:/usr/lib/cuda/lib64:/usr/local/lib/x86_64-linux-gnu:/usr/local/cuda/targets/x86_64-linux/lib:/usr/local/cuda/lib64:/home/elderos/soft/cuda:/home/elderos/soft/cuda/lib64
export PATH=/home/elderos/bin:/home/elderos/.local/bin:/usr/local/cuda/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/games:/usr/local/sbin:/usr/local/bin:/home/elderos/bin:/usr/local/cuda/targets/x86_64-linux/include:/usr/lib/gcc/x86_64-linux-gnu/4.9:/home/elderos/soft/cuda/include

python server.py -p 50000 >>stdout_log.txt 2>>stderr_log.txt
