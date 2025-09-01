export PATH=/mnt/petrelfs/share/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/mnt/petrelfs/share/cuda-12.1/lib64:$LD_LIBRARY_PATH

export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
export PATH=/mnt/petrelfs/share/gcc/gcc-11.2.0/bin:$PATH

# try gcc 9.4.0
# export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/gcc-9.4.0/lib64:${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
# export PATH=/mnt/petrelfs/share/gcc/gcc-9.4.0/bin:$PATH

# libmpfr.so.6
export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/mpfr-4.1.0/lib:$LD_LIBRARY_PATH
# libmpc.so.2
export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/mpc-0.8.1/lib:$LD_LIBRARY_PATH
# libmpfr.so.1
export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/mpfr-2.4.2/lib/:$LD_LIBRARY_PATH
# libgmp.so.3
export LD_LIBRARY_PATH=/mnt/petrelfs/share/gcc/gmp-4.3.2/lib/:$LD_LIBRARY_PATH

