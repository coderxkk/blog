.. meta::
   :description: HIPRTC 基础学习知识
   :keywords: HIPRTC, runtime compile, rtc, comgr

##############################
ROCm HIPRTC 基础
##############################


.. contents:: 目录
   :depth: 3
   :local:

1. HIPRTC 简介
===============================

HIPRTC（HIP Runtime Compilation）是 ROCm 提供的运行时编译库。

通常情况下，HIP Kernel 会在程序构建阶段通过 ``hipcc`` 或 ``amdclang++``
提前编译。例如：

.. code-block:: bash

   hipcc vector_add.cpp -o vector_add

而 HIPRTC 允许应用程序在 **运行时** 将字符串形式的 HIP C++ Kernel
编译成 GPU 可以执行的代码。

典型流程如下：

.. code-block:: text

   HIP C++ Source String
           |
           v
   hiprtcCreateProgram()
           |
           v
   hiprtcCompileProgram()
           |
           v
   hiprtcGetCode()
           |
           v
      GPU Code Object
           |
           v
   hipModuleLoadData()
           |
           v
   hipModuleGetFunction()
           |
           v
   hipModuleLaunchKernel()

因此，HIPRTC 可以理解为 ROCm 中与 NVIDIA CUDA NVRTC 类似的组件。

常见应用场景包括：

* JIT（Just-In-Time）Kernel 编译；
* 根据输入 Shape 动态生成 Kernel；
* 自动代码生成；
* Kernel Fusion；
* DSL 编译器；
* AI Compiler；
* 高性能计算框架；
* 动态生成针对特定 GPU 架构优化的 Kernel。

例如 Triton、深度学习编译器以及各种 Kernel Generator 都涉及与此类似的
Runtime Compilation 思想。


2. HIPRTC 在 ROCm 软件栈中的位置
==============================================================

从 ROCm 软件栈角度，可以大致将 HIPRTC 放在以下位置：

.. code-block:: text

                    Application
                        |
                        v
                 HIPRTC API
                        |
                hiprtcCompileProgram
                        |
                        v
                     COMGR
                        |
                 Clang / LLVM
                        |
                 LLVM AMDGPU
                   Backend
                        |
                        v
               AMD GPU Code Object
                        |
                        v
                HIP Module API
                        |
                hipModuleLoadData
                        |
                        v
                      CLR
                        |
                        v
                  ROCr Runtime
                     / HSA
                        |
                        v
                      KFD
                        |
                        v
                     GPU

这里可以把整个过程划分为两个阶段。

编译阶段：

.. code-block:: text

   HIP Source
       |
       v
    HIPRTC
       |
       v
     COMGR
       |
       v
   Clang/LLVM
       |
       v
   AMDGPU ISA
       |
       v
   Code Object

执行阶段：

.. code-block:: text

   Code Object
       |
       v
   hipModuleLoadData()
       |
       v
   HIP Runtime / CLR
       |
       v
      HSA
       |
       v
      KFD
       |
       v
      GPU

对于 Runtime 开发人员，这两个阶段的交界点非常值得关注：

::

   hiprtcGetCode()
          |
          | GPU Code Object
          v
   hipModuleLoadData()

HIPRTC 负责“生成代码”，HIP Runtime Module API 负责“加载并执行代码”。


3. HIPRTC 与普通 HIP 编译的区别
=============================================================

普通 HIP 编译通常发生在应用程序构建阶段：

.. code-block:: text

   kernel.cpp
       |
       v
     hipcc
       |
       v
   amdclang++
       |
       v
   Clang / LLVM
       |
       v
   Code Object
       |
       v
   Application

HIPRTC 则是在程序运行过程中执行：

.. code-block:: text

   Application Running
          |
          v
   Kernel Source String
          |
          v
   hiprtcCompileProgram()
          |
          v
      Code Object
          |
          v
   hipModuleLoadData()
          |
          v
        Execute

最核心的区别在于：

* ``hipcc``：Ahead-of-Time Compilation（AOT）；
* ``hiprtc``：Runtime Compilation / JIT Compilation。


4. HIPRTC 核心 API
================================================

HIPRTC API 定义在：

.. code-block:: cpp

   #include <hip/hiprtc.h>

其中最重要的几个 API 是：

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - API
     - 功能
   * - ``hiprtcCreateProgram()``
     - 创建一个 Runtime Compilation Program
   * - ``hiprtcCompileProgram()``
     - 编译 HIP C++ Source
   * - ``hiprtcGetProgramLogSize()``
     - 获取编译日志长度
   * - ``hiprtcGetProgramLog()``
     - 获取编译器日志
   * - ``hiprtcGetCodeSize()``
     - 获取编译后 binary 大小
   * - ``hiprtcGetCode()``
     - 获取编译产生的 binary
   * - ``hiprtcGetBitcodeSize()``
     - 获取 LLVM bitcode 大小
   * - ``hiprtcGetBitcode()``
     - 获取 LLVM bitcode
   * - ``hiprtcDestroyProgram()``
     - 销毁 ``hiprtcProgram``


5. hiprtcProgram
================

HIPRTC 最核心的数据结构之一是：

.. code-block:: cpp

   hiprtcProgram

可以简单将它理解成：

::

   一次 Runtime Compilation 的上下文

一个 ``hiprtcProgram`` 中通常保存：

* Kernel Source；
* Source Name；
* Header Source；
* Include 信息；
* Compiler Options；
* Compiler Log；
* 编译结果；
* LLVM Bitcode；
* GPU Binary。

典型生命周期为：

.. code-block:: text

   hiprtcProgram prog
          |
          v
   hiprtcCreateProgram()
          |
          v
   hiprtcCompileProgram()
          |
          +----------------------+
          |                      |
          v                      v
   hiprtcGetCode()       hiprtcGetProgramLog()
          |
          v
   hiprtcDestroyProgram()


6. 创建 HIPRTC Program
====================================================

最简单的 Kernel 可以直接保存在字符串中：

.. code-block:: cpp

   const char* kernel_source = R"(

   extern "C"
   __global__ void vector_add(const float* a,
                              const float* b,
                              float* c,
                              int n)
   {
       int i = blockIdx.x * blockDim.x + threadIdx.x;

       if (i < n)
           c[i] = a[i] + b[i];
   }

   )";

然后创建 ``hiprtcProgram``：

.. code-block:: cpp

   hiprtcProgram program;

   hiprtcResult result =
       hiprtcCreateProgram(
           &program,
           kernel_source,
           "vector_add.cpp",
           0,
           nullptr,
           nullptr);

参数含义：

::

   hiprtcCreateProgram(
       program,
       source,
       source_name,
       num_headers,
       headers,
       include_names
   )

这里没有使用额外头文件，因此：

::

   num_headers   = 0
   headers       = nullptr
   include_names = nullptr


7. Runtime 编译
=============================================

创建 Program 后，可以调用：

.. code-block:: cpp

   hiprtcCompileProgram()

例如：

.. code-block:: cpp

   hiprtcResult result =
       hiprtcCompileProgram(
           program,
           0,
           nullptr);

如果需要指定编译参数：

.. code-block:: cpp

   const char* options[] = {
       "-O3",
       "--gpu-architecture=gfx942"
   };

   hiprtcCompileProgram(
       program,
       2,
       options);

其中：

::

   -O3

表示开启优化。

而：

::

   --gpu-architecture=gfx942

表示为指定 GPU Architecture 生成代码。

``--gpu-architecture`` 与 ``--offload-arch`` 的用途类似。


8. 获取当前 GPU Architecture
==========================================================

Runtime Compilation 时通常希望针对当前 GPU 生成代码。

可以通过 HIP Runtime 获取设备属性：

.. code-block:: cpp

   hipDeviceProp_t props;

   hipGetDeviceProperties(&props, 0);

   std::cout << props.gcnArchName << std::endl;

例如可能得到：

::

   gfx90a
   gfx942
   gfx1100

然后构造 HIPRTC 编译参数：

.. code-block:: cpp

   std::string arch =
       std::string("--gpu-architecture=") +
       props.gcnArchName;

   const char* options[] = {
       arch.c_str()
   };

   hiprtcCompileProgram(
       program,
       1,
       options);

在没有可用 AMD GPU 的机器上进行离线 Runtime Compilation 时，
显式提供 GPU Architecture 尤其重要。


9. 获取编译日志
=============================================

学习 HIPRTC 时强烈建议始终读取 Compiler Log。

首先获取日志大小：

.. code-block:: cpp

   size_t log_size = 0;

   hiprtcGetProgramLogSize(
       program,
       &log_size);

然后读取日志：

.. code-block:: cpp

   std::vector<char> log(log_size);

   if (log_size > 0) {
       hiprtcGetProgramLog(
           program,
           log.data());

       std::cout << log.data()
                 << std::endl;
   }

当 Kernel 出现：

* Syntax Error；
* Type Error；
* Unsupported Feature；
* Invalid Compiler Option；
* Template Error；

时，可以通过这里查看 Clang Compiler 的错误信息。

从这一点也可以看到 HIPRTC 和 Clang/LLVM 之间的紧密关系。


10. 获取 GPU Binary
=================================================

编译成功之后：

.. code-block:: cpp

   size_t code_size = 0;

   hiprtcGetCodeSize(
       program,
       &code_size);

然后分配内存：

.. code-block:: cpp

   std::vector<char> code(code_size);

再获取 Binary：

.. code-block:: cpp

   hiprtcGetCode(
       program,
       code.data());

此时可以简单理解为：

.. code-block:: text

   HIP C++ Source
          |
          v
   hiprtcCompileProgram
          |
          v
   hiprtcGetCode
          |
          v
      GPU Binary

对于 AMD GPU，最终结果通常涉及 AMD GPU Code Object。


11. 使用 HIP Module API 加载 Binary
=================================================================

HIPRTC 只负责 Runtime Compilation。

如果希望真正执行 Kernel，还需要 HIP Runtime 的 Module API。

首先加载 Code Object：

.. code-block:: cpp

   hipModule_t module;

   hipModuleLoadData(
       &module,
       code.data());

然后查找 Kernel：

.. code-block:: cpp

   hipFunction_t function;

   hipModuleGetFunction(
       &function,
       module,
       "vector_add");

完整流程变成：

.. code-block:: text

   HIP Source
       |
       v
   hiprtcCreateProgram
       |
       v
   hiprtcCompileProgram
       |
       v
   hiprtcGetCode
       |
       v
   Code Object
       |
       v
   hipModuleLoadData
       |
       v
   hipModuleGetFunction
       |
       v
   hipModuleLaunchKernel


12. 为什么使用 extern "C"
=======================================================

示例 Kernel 使用了：

.. code-block:: cpp

   extern "C"
   __global__ void vector_add(...)

原因是 C++ Compiler 会进行 Name Mangling。

例如：

::

   vector_add

经过 C++ 编译之后可能变成类似：

::

   _Z10vector_addPKfS0_Pfi

这样：

.. code-block:: cpp

   hipModuleGetFunction(
       &function,
       module,
       "vector_add");

就无法直接查找到对应 Kernel。

对于简单学习程序，可以使用：

::

   extern "C"

避免 Name Mangling。

对于 Template Kernel、重载函数等复杂情况，则可以学习 HIPRTC 提供的：

::

   hiprtcAddNameExpression()

和：

::

   hiprtcGetLoweredName()

来获取真正的 Lowered / Mangled Name。


13. 最小 HIPRTC 示例
==================================================

下面给出一个较完整的示例。

文件：

::

   hiprtc_basic.cpp

内容：

.. code-block:: cpp

   #include <hip/hip_runtime.h>
   #include <hip/hiprtc.h>

   #include <cstdlib>
   #include <iostream>
   #include <string>
   #include <vector>

   #define HIP_CHECK(call)                                      
       do {                                                     
           hipError_t err = (call);                             
           if (err != hipSuccess) {                             
               std::cerr << "HIP error: "                       
                         << hipGetErrorString(err)               
                         << std::endl;                           
               std::exit(EXIT_FAILURE);                         
           }                                                    
       } while (0)

   #define HIPRTC_CHECK(call)                                   
       do {                                                     
           hiprtcResult err = (call);                           
           if (err != HIPRTC_SUCCESS) {                         
               std::cerr << "HIPRTC error: "                    
                         << hiprtcGetErrorString(err)            
                         << std::endl;                           
               std::exit(EXIT_FAILURE);                         
           }                                                    
       } while (0)

   static const char* kernel_source = R"(

   extern "C"
   __global__ void vector_add(const float* a,
                              const float* b,
                              float* c,
                              int n)
   {
       int i = blockIdx.x * blockDim.x + threadIdx.x;

       if (i < n)
           c[i] = a[i] + b[i];
   }

   )";

   int main()
   {
       hiprtcProgram program;

       HIPRTC_CHECK(
           hiprtcCreateProgram(
               &program,
               kernel_source,
               "vector_add.cpp",
               0,
               nullptr,
               nullptr));

       hipDeviceProp_t props;

       HIP_CHECK(
           hipGetDeviceProperties(
               &props,
               0));

       std::cout << "GPU architecture: "
                 << props.gcnArchName
                 << std::endl;

       std::string arch_option =
           std::string("--gpu-architecture=") +
           props.gcnArchName;

       const char* options[] = {
           arch_option.c_str(),
           "-O3"
       };

       hiprtcResult compile_result =
           hiprtcCompileProgram(
               program,
               2,
               options);

       size_t log_size = 0;

       HIPRTC_CHECK(
           hiprtcGetProgramLogSize(
               program,
               &log_size));

       if (log_size > 1) {

           std::vector<char> log(log_size);

           HIPRTC_CHECK(
               hiprtcGetProgramLog(
                   program,
                   log.data()));

           std::cout
               << "Compiler log:"
               << std::endl
               << log.data()
               << std::endl;
       }

       if (compile_result != HIPRTC_SUCCESS) {

           std::cerr
               << "hiprtcCompileProgram failed: "
               << hiprtcGetErrorString(
                      compile_result)
               << std::endl;

           hiprtcDestroyProgram(&program);

           return EXIT_FAILURE;
       }

       size_t code_size = 0;

       HIPRTC_CHECK(
           hiprtcGetCodeSize(
               program,
               &code_size));

       std::vector<char> code(
           code_size);

       HIPRTC_CHECK(
           hiprtcGetCode(
               program,
               code.data()));

       std::cout
           << "Generated code size: "
           << code_size
           << " bytes"
           << std::endl;

       HIPRTC_CHECK(
           hiprtcDestroyProgram(
               &program));

       hipModule_t module;
       hipFunction_t function;

       HIP_CHECK(
           hipModuleLoadData(
               &module,
               code.data()));

       HIP_CHECK(
           hipModuleGetFunction(
               &function,
               module,
               "vector_add"));

       constexpr int N = 1024;

       std::vector<float> h_a(N, 1.0f);
       std::vector<float> h_b(N, 2.0f);
       std::vector<float> h_c(N, 0.0f);

       float* d_a = nullptr;
       float* d_b = nullptr;
       float* d_c = nullptr;

       HIP_CHECK(
           hipMalloc(
               &d_a,
               N * sizeof(float)));

       HIP_CHECK(
           hipMalloc(
               &d_b,
               N * sizeof(float)));

       HIP_CHECK(
           hipMalloc(
               &d_c,
               N * sizeof(float)));

       HIP_CHECK(
           hipMemcpy(
               d_a,
               h_a.data(),
               N * sizeof(float),
               hipMemcpyHostToDevice));

       HIP_CHECK(
           hipMemcpy(
               d_b,
               h_b.data(),
               N * sizeof(float),
               hipMemcpyHostToDevice));

       struct KernelArgs {
           const float* a;
           const float* b;
           float* c;
           int n;
       };

       KernelArgs args {
           d_a,
           d_b,
           d_c,
           N
       };

       size_t args_size =
           sizeof(args);

       void* config[] = {
           HIP_LAUNCH_PARAM_BUFFER_POINTER,
           &args,

           HIP_LAUNCH_PARAM_BUFFER_SIZE,
           &args_size,

           HIP_LAUNCH_PARAM_END
       };

       constexpr int block_size = 256;

       int grid_size =
           (N + block_size - 1) /
           block_size;

       HIP_CHECK(
           hipModuleLaunchKernel(
               function,
               grid_size,
               1,
               1,
               block_size,
               1,
               1,
               0,
               nullptr,
               nullptr,
               config));

       HIP_CHECK(
           hipDeviceSynchronize());

       HIP_CHECK(
           hipMemcpy(
               h_c.data(),
               d_c,
               N * sizeof(float),
               hipMemcpyDeviceToHost));

       std::cout
           << "c[0] = "
           << h_c[0]
           << std::endl;

       HIP_CHECK(hipFree(d_a));
       HIP_CHECK(hipFree(d_b));
       HIP_CHECK(hipFree(d_c));

       HIP_CHECK(
           hipModuleUnload(module));

       return 0;
   }


14. 编译和运行
============================================

可以使用 ``hipcc`` 编译 Host 程序：

.. code-block:: bash

   hipcc 
       -std=c++17 
       hiprtc_basic.cpp 
       -o hiprtc_basic 
       -lhiprtc

执行：

.. code-block:: bash

   ./hiprtc_basic

正常情况下会看到类似：

.. code-block:: text

   GPU architecture: gfx942
   Generated code size: ...
   c[0] = 3


15. HIPRTC 与 COMGR
=================================================

如果只从 API 使用角度学习，到这里已经可以完成基本 HIPRTC 编程。

但对于 ROCm Runtime / Compiler 开发人员，还需要继续理解：

::

   hiprtcCompileProgram()

内部究竟发生了什么。

一个非常重要的组件是：

::

   AMD COMGR
   AMD Code Object Manager

HIPRTC 的底层编译过程会利用 COMGR。

可以建立如下概念模型：

.. code-block:: text

   hiprtcCompileProgram()
             |
             v
           HIPRTC
             |
             v
           COMGR
             |
             v
        Clang Frontend
             |
             v
          LLVM IR
             |
             v
      Optimization Passes
             |
             v
       AMDGPU Backend
             |
             v
         AMDGPU ISA
             |
             v
        Code Object

因此：

::

   HIPRTC

更像 Runtime Compilation API 层。

而：

::

   COMGR + Clang + LLVM

才是真正执行大量 Compiler 工作的位置。


16. LLVM Bitcode 模式
===================================================

正常情况下：

.. code-block:: text

   HIP Source
       |
       v
   hiprtcCompileProgram
       |
       v
   ISA / Code Object

但是 HIPRTC 还支持生成 LLVM Bitcode。

编译时加入：

::

   -fgpu-rdc

例如：

.. code-block:: cpp

   const char* options[] = {
       "-fgpu-rdc"
   };

   hiprtcCompileProgram(
       program,
       1,
       options);

此时可以使用：

.. code-block:: cpp

   size_t bitcode_size;

   hiprtcGetBitcodeSize(
       program,
       &bitcode_size);

   std::vector<char> bitcode(
       bitcode_size);

   hiprtcGetBitcode(
       program,
       bitcode.data());

流程变为：

.. code-block:: text

   HIP Source
       |
       v
   HIPRTC
       |
       v
   Clang
       |
       v
    LLVM IR
       |
       v
   LLVM Bitcode
       |
       X
   暂时不生成最终 ISA

这样可以在 Runtime 继续执行：

* Device Linking；
* LTO；
* 多个 Bitcode 合并；
* Runtime Optimization。


17. HIPRTC Runtime Linking
========================================================

HIPRTC 还提供 Runtime Linker API。

重要 API 包括：

::

   hiprtcLinkCreate()

   hiprtcLinkAddData()

   hiprtcLinkAddFile()

   hiprtcLinkComplete()

   hiprtcLinkDestroy()

基本流程如下：

.. code-block:: text

          HIP Source A
               |
               v
           LLVM BC A
               |
               |
               +-------------+
                             |
                             v
                       hiprtcLinkAddData
                             |
                             |
          HIP Source B       |
               |             |
               v             |
           LLVM BC B         |
               |             |
               +-------------+
                             |
                             v
                     hiprtcLinkComplete
                             |
                             v
                       Final Binary
                             |
                             v
                     hipModuleLoadData

这一能力对于：

* Runtime Kernel Composition；
* Kernel Library；
* Dynamic Device Linking；
* JIT Compiler；
* DSL；

非常重要。


18. HIPRTC 和 CUDA NVRTC 对比
===========================================================

从概念上可以建立如下对应：

.. list-table::
   :header-rows: 1
   :widths: 40 40

   * - CUDA
     - ROCm
   * - NVRTC
     - HIPRTC
   * - ``nvrtcProgram``
     - ``hiprtcProgram``
   * - ``nvrtcCreateProgram``
     - ``hiprtcCreateProgram``
   * - ``nvrtcCompileProgram``
     - ``hiprtcCompileProgram``
   * - ``nvrtcGetProgramLog``
     - ``hiprtcGetProgramLog``
   * - ``nvrtcGetPTX``
     - ``hiprtcGetCode`` / ``hiprtcGetBitcode``
   * - CUDA Driver Module API
     - HIP Module API
   * - ``cuModuleLoadData``
     - ``hipModuleLoadData``
   * - ``cuModuleGetFunction``
     - ``hipModuleGetFunction``
   * - ``cuLaunchKernel``
     - ``hipModuleLaunchKernel``

需要注意：

CUDA 与 ROCm 的内部 Compiler Pipeline 并不是完全相同的，
因此这个表主要用于帮助建立 API 层面的对应关系。


19. 推荐的调试调用链
==================================================

如果目标是研究 HIPRTC 底层实现，可以从：

::

   hiprtcCompileProgram()

开始设置断点。

建议按照下面的方向跟踪：

.. code-block:: text

   Application

       hiprtcCompileProgram()
                |
                v
             HIPRTC
                |
                v
              COMGR
                |
                v
             Clang
                |
                v
             LLVM IR
                |
                v
          AMDGPU Backend
                |
                v
            Code Object

随后继续跟：

.. code-block:: text

   hipModuleLoadData()
          |
          v
       HIP CLR
          |
          v
     Code Object Loader
          |
          v
         HSA
          |
          v
         KFD

这样就可以把：

::

   Compiler Stack

和：

::

   Runtime Stack

连接起来。


20. 推荐学习顺序
==============================================

第一阶段：掌握 HIPRTC API
-------------------------

首先掌握：

::

   hiprtcCreateProgram

   hiprtcCompileProgram

   hiprtcGetProgramLog

   hiprtcGetCode

   hiprtcDestroyProgram

目标是能够独立完成：

::

   Source String
        ->
   Runtime Compile
        ->
   Binary


第二阶段：掌握 Module API
-------------------------

学习：

::

   hipModuleLoadData

   hipModuleGetFunction

   hipModuleLaunchKernel

目标是理解：

::

   HIPRTC
      |
      v
   Code Object
      |
      v
   HIP Runtime
      |
      v
     GPU


第三阶段：研究 Bitcode
-------------------------------------------

学习：

::

   -fgpu-rdc

   hiprtcGetBitcode

   hiprtcGetBitcodeSize

重点理解：

::

   HIP Source
       ->
   LLVM IR
       ->
   LLVM Bitcode


第四阶段：研究 Runtime Linking
--------------------------------------------------

学习：

::

   hiprtcLinkCreate

   hiprtcLinkAddData

   hiprtcLinkComplete

理解：

::

   BC A
     
      +--> Runtime Link --> Code Object
     /
   BC B


第五阶段：研究源码实现
-----------------------------------------------

重点关注：

::

   HIPRTC
      |
      v
   COMGR
      |
      v
   Clang
      |
      v
   LLVM
      |
      v
   AMDGPU Backend


21. 建议实验
==========================================

实验一
------

编写最简单的：

::

   vector_add

Kernel。

完成：

::

   HIP Source
       ->
   hiprtcCompileProgram
       ->
   hiprtcGetCode


实验二
------

使用：

::

   hipModuleLoadData

加载实验一生成的 Binary。


实验三
------

使用：

::

   hipModuleGetFunction

获取 Kernel。


实验四
------

使用：

::

   hipModuleLaunchKernel

真正执行 Runtime 编译的 Kernel。


实验五
------

增加错误代码：

.. code-block:: cpp

   this_is_invalid_code

然后观察：

::

   hiprtcGetProgramLog()

输出的 Clang Compiler Error。


实验六
------

分别使用：

::

   -O0

和：

::

   -O3

生成 Code Object。

使用 AMDGPU Disassembler 比较生成的 ISA。


实验七
------

加入：

::

   -fgpu-rdc

获取 LLVM Bitcode。

观察：

::

   HIP Source
      ->
   LLVM Bitcode


实验八
------

使用 HIPRTC Linker：

::

   hiprtcLinkCreate
       |
       v
   hiprtcLinkAddData
       |
       v
   hiprtcLinkComplete


22. 进一步学习方向
================================================

掌握 HIPRTC 基础之后，推荐继续研究以下内容：

::

   HIPRTC

       |
       +---- COMGR
       |
       +---- Clang
       |
       +---- LLVM IR
       |
       +---- AMDGPU Backend
       |
       +---- AMDGPU ISA
       |
       +---- Code Object
       |
       +---- ELF
       |
       +---- hipModuleLoadData
       |
       +---- CLR
       |
       +---- HSA
       |
       +---- KFD

最终可以形成一条完整的 ROCm Runtime Compilation 调用链：

.. code-block:: text

   HIP Kernel Source
          |
          v
        HIPRTC
          |
          v
        COMGR
          |
          v
     Clang Frontend
          |
          v
       LLVM IR
          |
          v
    LLVM Optimizer
          |
          v
    AMDGPU Backend
          |
          v
      AMDGPU ISA
          |
          v
    AMD Code Object
          |
          v
   hipModuleLoadData
          |
          v
       HIP CLR
          |
          v
         HSA
          |
          v
         KFD
          |
          v
      AMD GPU


23. 学习重点总结
==============================================

对于初学 HIPRTC，最重要的是首先理解下面这条主线：

::

   hiprtcCreateProgram
          |
          v
   hiprtcCompileProgram
          |
          v
     hiprtcGetCode
          |
          v
   hipModuleLoadData
          |
          v
   hipModuleGetFunction
          |
          v
   hipModuleLaunchKernel

对于 Runtime / UMD 开发人员，则应该进一步扩展成：

::

   hiprtcCompileProgram
          |
          v
        HIPRTC
          |
          v
        COMGR
          |
          v
    Clang / LLVM
          |
          v
    AMDGPU Backend
          |
          v
      Code Object
          |
          v
   hipModuleLoadData
          |
          v
        CLR
          |
          v
        HSA
          |
          v
        KFD

前一条链解决：

::

   HIPRTC 怎么用？

后一条链解决：

::

   HIPRTC 为什么能够工作？
   hiprtcCompileProgram 内部到底发生了什么？

对于 ROCm Runtime 开发人员，第二条链通常具有更高的源码学习价值。


24. 参考资料
==========================================

ROCm HIPRTC 官方文档：

`Programming for HIP runtime compiler (RTC)
<https://rocm.docs.amd.com/projects/HIP/en/latest/how-to/hip_rtc.html>`_

HIPRTC API：

`hiprtc.h API Reference
<https://rocm.docs.amd.com/projects/HIP/en/develop/doxygen/html/hiprtc_8h_source.html>`_

HIP Module API：

`HIP Module Management
<https://rocm.docs.amd.com/projects/HIP/en/latest/reference/hip_runtime_api/modules/module_management.html>`_

ROCm Examples：

`ROCm Examples
<https://github.com/ROCm/rocm-examples>`_

后续学习 COMGR 时建议重点阅读 ROCm LLVM 工程中的：

::

   amd/comgr

以及：

::

   amd/device-libs