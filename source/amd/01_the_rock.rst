.. meta::
   :description: 初探 TheRock 工具
   :keywords: TheRock, ROCm, 构建, 发布，持续集成

##############################
TheRock--rocm构建工具
##############################

TheRock 使用方法
==================

拉取代码
--------------------------

.. code-block:: shell

    mkdir -p ~/rocm-dev
    cd ~/rocm-dev

    git clone https://github.com/ROCm/TheRock.git
    cd TheRock

不要手动 git submodule update --init --recursive。TheRock 当前推荐：

.. code-block:: shell

    python3 ./build_tools/fetch_sources.py

.. note::

    由于网络连接不稳定或仓库体积过大，导致在传输过程中连接被意外中断。
    可以在拉取子模块代码前，可以调整git的网络配置避免网络问题。

    .. code-block:: shell

        # 增加 HTTP 缓冲区大小（约 500MB）
        git config --global http.postBuffer 524288000

        # 将 HTTP 版本切换为 1.1，通常比 2.0 更稳定
        git config --global http.version HTTP/1.1

        # 设置低速限制，避免因短暂速度慢而超时
        git config --global http.lowSpeedLimit 0
        git config --global http.lowSpeedTime 999999


可以通过以下语句拉取子模块代码并查看拉取进度

.. code-block:: shell

    # 以拉取 rocm-libraries 子模块 为例
    git submodule update --init --progress -- rocm-libraries

stage构建说明
--------------------------


当然也可以只编译部分代码。可以用 --stage 特性构建其中的子模块。

.. code-block:: shell

    # 只构建 rocm-libraries
    python3 ./build_tools/build.py --stage compiler-runtime

The Rock 的 12 个 stages 分为四种角色，如下图所示：

.. raw:: html

   <div style="padding:8px 0 4px;font-size:15px;font-weight:600;color:#1A1B1C;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;">The Rock 的 12 个 stages · 四种角色（示意）</div>

   <div style="margin:12px 0 0;padding:10px 14px;background:linear-gradient(135deg, rgba(163,213,232,0.22), rgba(163,213,232,0.38));border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
     <div style="font-size:11px;color:#55606E;">① 地基 · 必须先建完，其他 stage 都依赖它</div>
     <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:3px;">compiler-runtime <span style="font-size:10.5px;font-weight:400;color:#6B7280;">(generic)</span></div>
     <div style="font-size:11px;color:#55606E;margin-top:2px;">LLVM 编译器 + HIP/OpenCL 运行时 + profiler-core + amdsmi + 系统库</div>
     <div style="text-align:center;font-size:12px;color:#6B7280;margin-top:6px;">↓ 喂给下面所有 stage</div>
   </div>

   <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 0;">
     <div style="flex:1 1 150px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.035);border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:11px;color:#55606E;">② 房间 · 五类库，彼此并行</div>
       <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:3px;">math-libs <span style="font-size:10.5px;font-weight:400;color:#B5472D;background:#FDE9E4;border-radius:6px;padding:1px 5px;">per-arch</span></div>
       <div style="font-size:11px;color:#55606E;margin-top:2px;">BLAS/FFT/求解器/MIOpen，每种 GPU 架构编一份</div>
     </div>
     <div style="flex:1 1 110px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.035);border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:14px;">comm-libs</div>
       <div style="font-size:11px;color:#55606E;margin-top:2px;">RCCL 多卡通信</div>
     </div>
     <div style="flex:1 1 110px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.035);border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:14px;">storage-libs</div>
       <div style="font-size:11px;color:#55606E;margin-top:2px;">存储库</div>
     </div>
     <div style="flex:1 1 110px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.035);border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:14px;">cv-libs</div>
       <div style="font-size:11px;color:#55606E;margin-top:2px;">MIVisionX 视觉库</div>
     </div>
     <div style="flex:1 1 130px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.035);border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:13px;font-weight:600;color:#1A1B1C;margin-top:14px;">media-libs</div>
       <div style="font-size:11px;color:#55606E;margin-top:2px;">Mesa VA-API + 视频解码</div>
     </div>
   </div>

   <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 0;">
     <div style="flex:1 1 200px;min-width:0;padding:10px 12px;background:rgba(26,27,28,0.025);border:0.5px dashed rgba(0,0,0,0.12);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:11px;color:#55606E;">③ 测试/特殊</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:3px;">runtime-tests（测运行时）</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:2px;">emulation（CPU 仿真）</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:2px;">wsl-rocdxg（仅 WSL）</div>
     </div>
     <div style="flex:1 1 200px;min-width:0;padding:10px 12px;background:linear-gradient(135deg, rgba(148,212,208,0.12), rgba(148,212,208,0.24));border:0.5px solid rgba(0,0,0,0.08);border-radius:12px;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;box-sizing:border-box;">
       <div style="font-size:11px;color:#55606E;">④ 工具 · 开发者最终使用</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:3px;">debug-tools（rocgdb 调试器）</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:2px;">dctools-core（RDC 数据中心管理）</div>
       <div style="font-size:12.5px;color:#1A1B1C;margin-top:2px;">profiler-apps（rocprof 性能分析）</div>
     </div>
   </div>

   <div style="margin:10px 0 2px;font-size:11px;color:#6B7280;font-family:'Roboto','PingFang SC','Segoe UI',Arial,sans-serif;">图例：generic = 编一次全平台通用；per-arch = 按每种 GPU 架构各编一份。图为角色分组示意，精确依赖见 BUILD_TOPOLOGY.toml。</div>


`BUILD_TOPOLOGY.toml` 是构建拓扑的唯一事实源。

The Rock（The HIP Environment and ROCm Kit）是 ROCm 自 7.14 起官方采用的构建与发布系统，一个 CMake super-project，把整个 ROCm 拆成多个 build stage（对应 CI 流水线任务），每个 stage 负责构建一组 artifact group（逻辑相关的产物分组），group 之间通过依赖关系串联，支持并行分片构建和按需部分签出（每个 stage 只 clone 自己需要的 submodule）。

如下是BUILD_TOPOLOGY.toml 的官方注释说明：

.. code-block:: toml

    # ==============================================================================
    # BUILD_TOPOLOGY.toml - TheRock 构建拓扑元数据
    # ==============================================================================
    #
    # 本文件是 TheRock 构建产物结构的唯一事实源。
    # 它有三个主要用途：
    #
    #   1. CMake Feature 生成：在配置（configure）阶段，topology_to_cmake.py 读取
    #      本文件，为每个产物生成 therock_add_feature() 调用，
    #      创建控制构建的 THEROCK_ENABLE_* 缓存变量。
    #
    #   2. CI/CD 流水线分片：build_topology.py 模块解析本文件，
    #      计算分片构建所需的产物依赖，确定每个 stage 开始前
    #      需要从产物存储中拉取哪些产物。
    #
    #   3. 部分源码签出：源码集（source sets）定义了每个产物组所需的
    #      git 子模块，使 CI 任务只需克隆其构建阶段所需的子模块
    #      （通过 fetch_sources.py --stage 实现）。
    #
    # 层级结构：
    #   - 源码集（Source Sets）    - git 子模块的分组，用于部分签出
    #   - 构建阶段（Build Stages） - 构建一组产物组的 CI/CD 流水线任务
    #   - 产物组（Artifact Groups）- 具有共享依赖的相关产物的逻辑分组
    #   - 产物（Artifacts）        - 单个构建输出（最基本的打包单元）
    #
    # 命名约定：
    #   - 实体名（stages、groups、artifacts）：小写加连字符（例如 "core-runtime"）
    #   - feature_name：大写加下划线（例如 "CORE_RUNTIME"）—— 映射到 THEROCK_ENABLE_*
    #   - feature_group：大写加下划线（例如 "CORE"）—— 映射到组选项
    #   - type 取值：小写（例如 "generic"、"per-arch"、"target-neutral"、"target-specific"）
    #   - platform 取值：小写（例如 "windows"、"linux"）
    #
    # 配置项参考：
    #
    #   [source_sets.<name>]
    #   description = "人类可读的描述"
    #   submodules = ["submodule1", "submodule2"]  # git 子模块目录名
    #   external_git_sources = [
    #     { name = "name", origin = "https://...", commit = "hash", path = "optional-sources/name" },
    #   ]                                         # 可选：外部拉取的 git 仓库
    #   disable_platforms = ["windows"]            # 可选：禁用的平台
    #
    #   [build_stages.<name>]
    #   description = "人类可读的描述"
    #   artifact_groups = ["group1", "group2"]  # 该 stage 构建的产物组
    #   type = "generic" | "per-arch"           # 可选，默认为 "generic"
    #
    #   [artifact_groups.<name>]
    #   description = "人类可读的描述"
    #   type = "generic" | "per-arch"           # "per-arch" = 按 GPU 架构分别构建
    #   artifact_group_deps = ["dep1", "dep2"]  # 可选：本组依赖的其他组
    #   source_sets = ["set1", "set2"]          # 可选：本组所需的源码集
    #
    #   [artifacts.<name>]
    #   artifact_group = "group-name"           # 必填：该产物所属的产物组
    #   type = "target-neutral" | "target-specific"
    #       target-neutral：一次构建涵盖所有架构目标。适用于仅主机端代码、
    #           头文件或运行时库等更倾向于单一多架构构建的场景。
    #       target-specific：按架构家族分别构建，并保持分离以便分发。
    #           适用于内核（kernel）库，分片构建可提升 CI 并行度，
    #           并支持按架构（per-arch）下载。
    #   artifact_deps = ["dep1", "dep2"]        # 可选：该产物依赖的其他产物
    #   feature_name = "FEATURE_NAME"           # 可选：覆盖自动生成的名称
    #   feature_group = "GROUP_NAME"            # 可选：覆盖自动生成的组
    #   platform = "windows"                    # 可选：平台特定产物
    #   disable_platforms = ["windows"]         # 可选：禁用的平台
    #   disable_platforms_if_flags_not_set = { windows = "FOO" }  # 可选：条件性平台禁用
    #   disable_processors = ["aarch64"]     # 可选：禁用的 CPU 处理器
    #                                           #   规范名称：x86_64, aarch64, ppc64le
    #   python_requires = ["-r path/to/req.txt", "pkg"]  # 可选：pip 安装参数
    #   split_databases = ["rocblas", "hipblaslt"]  # 可选：kpack 分包的数据库处理器
    #   source_paths = ["path1", "path2"]         # 可选：映射到该产物的单仓（monorepo）
    #      子目录名。用于细粒度的 CI 产物复用：当外部仓库（如 rocm-libraries）中
    #      只有特定源码路径发生变化时，仅受影响产物重新构建，其余复用基线产物。
    #      路径名是 projects/ 或 shared/ 子目录下的目录基名。
    #      多个产物可以共享同一 source_path（例如共享库）。
    #      省略时默认为 [artifact_name]。
    #
    # ==============================================================================


构建开发容器
--------------------------

在程序编译前，建议先构建一个开发容器，可以在相对独立的环境进行开发。避免影响宿主机环境。
建一个专门的 TheRock 开发镜像，在 ~/rocm-dev/ 下创建：

.. code-block:: dockerfile

    # Dockerfile.therock-dev
    FROM ubuntu:24.04

    ENV DEBIAN_FRONTEND=noninteractive

    RUN apt-get update && apt-get install -y \
        ca-certificates \
        curl \
        git \
        gcc \
        g++ \
        gfortran \
        cmake \
        ninja-build \
        make \
        pkg-config \
        xxd \
        automake \
        autoconf \
        libtool \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libegl1-mesa-dev \
        texinfo \
        bison \
        flex \
        gdb \
        strace \
        ltrace \
        file \
        pciutils \
        vim \
        less \
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /workspace

    CMD ["/bin/bash"]

构建：

.. code-block:: shell

    cd ~/rocm-dev

    docker build \
        -f Dockerfile.therock-dev \
        -t therock-dev:ubuntu24.04 \
        .

容器启动：

.. code-block:: shell

    docker run -it \
        --name therock-dev \
        --device=/dev/kfd \
        --device=/dev/dri \
        --cap-add=SYS_PTRACE \
        --security-opt seccomp=unconfined \
        -v ~/my/rocm-dev/TheRock:/workspace/TheRock \
        -w /workspace/TheRock \
        therock-dev:ubuntu24.04

编译
--------------------------

