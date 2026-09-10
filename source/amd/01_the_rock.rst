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

