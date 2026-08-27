.. meta::
   :description: 初探 amdgpu 内核驱动源码
   :keywords: amdgpu, ROCm, 内核驱动, 源码

##########
初探amdgpu
##########

==========
amdgpu源码
==========

拉取代码

.. code-block:: shell

    git clone --depth 1 https://github.com/ROCm/amdgpu.git

amd驱动代码目录

.. code-block:: shell

    ls drivers/gpu/drm/amd/

==========
amdgpu简介
==========

参考 `AMD GPU Driver (amdgpu) 31.50.0 官方文档 <https://instinct.docs.amd.com/projects/amdgpu-docs/en/latest/index.html>`_。

AMD 当前官方仓库是 `ROCm/amdgpu <https://github.com/ROCm/amdgpu>`_，它是 ROCm 使用的 AMDGPU 内核源码分支；旧资料里的 ``ROCK-Kernel-Driver`` 可以视为它的历史名称/地址。

AMD GPU 驱动程序 (amdgpu) 是一款开源软件。它是软件生态系统（包括 ROCm 用户空间、AMD GPU 虚拟化和各类框架）中的关键组件，能够确保数据中心内强大的 AMD GPU 在 AI 和 HPC 应用负载下发挥最佳性能。
