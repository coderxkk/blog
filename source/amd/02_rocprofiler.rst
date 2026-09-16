.. meta::
   :description: 初探 rocprofiler 工具
   :keywords: rocprofiler, profiler, 性能分析

##############################
rocprofiler性能分析工具
##############################

rocprofiler 介绍
==================

.. important::
    ROCProfiler、`ROCTracer <https://rocm.docs.amd.com/projects/roctracer/en/latest/index.html>`_、``rocprof`` 和 ``rocprofv2`` 均已废弃。强烈建议升级至最新版
    `ROCprofiler-SDK <https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/install/installation.html>`_
    库以及 `rocprofv3 <https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html>`_ 工具，以持续获得技术支持并使用新特性。

    如需了解 ROCprofiler-SDK 相对旧版 ROCProfiler、ROCTracer 的关键特性提升与优势，请参阅
    `ROCprofiler-SDK 与传统 ROCm 分析工具对比 <https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/conceptual/comparing-with-legacy-tools.html>`_。

    ROCProfiler、ROCTracer、``rocprof`` 和 ``rocprofv2`` 预计将于 2026 年第二季度末停止维护（EoS）。

ROCProfiler 是 AMD 的工具基础设施，提供硬件相关的底层性能分析接口，用于对 GPU 计算应用进行性能采集与追踪。

ROCprofiler‑SDK 简介( `官方 <https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/>`_ )
-------------------------------------------------------------------------------------------------------------

ROCprofiler‑SDK 是一套面向 ROCm 软件平台上通用 GPU 计算应用的性能分析工具基础设施。
它支持 **应用程序追踪** ，能够完整呈现 GPU 应用的整体执行流程；同时支持 **kernel硬件计数器采集** ，可从硬件性能计数器获取底层硬件运行细节。

ROCprofiler‑SDK 库提供 **与运行时无关的 API** ，可对运行时调用、GPU 内核派发、内存拷贝等异步行为进行追踪。追踪能力包含两类接口：用于运行时 API 追踪的回调 API，以及用于记录异步行为日志的活动记录 API。

简言之，ROCprofiler‑SDK 整合了原 **ROCProfiler** 和 **ROCTracer** 两大组件。开发者可基于 ROCprofiler‑SDK 开发工具，对 ROCm 平台上的 HIP 应用做性能分析与运行追踪AMD ROCm。

本项目为开源项目，代码仓库托管于：ROCm/rocm‑systems。

.. note:: 

    ROCm 7.0 及更早版本的 ROCprofiler‑SDK 仓库地址为：ROCm/rocprofiler‑SDK。

ROCprofiler‑SDK 依赖配套库 **AQLprofile**，该库负责生成性能计数器、SQ 线程追踪所需的分析命令包（AQL/PM4）。更多信息请查阅 AQLprofile 文档。

rocprofv3
--------------------------

rocprofv3 是基于 rocprofiler-sdk 库开发的命令行工具，随 ROCm 软件栈一同发布。它既可以启动应用并开启性能剖析，也可以通过 `--attach` / `--pid` / `-p` 参数挂载到已经运行的进程，实现动态性能采集。

如需查看 rocprofv3 完整命令行选项，请参阅 `rocprofv3 用户手册 <https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/install/install.html>`_ 。

rocprofiler 使用方法
===========================

