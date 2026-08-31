.. meta::
   :description: 初探 amdgpu 内核驱动源码
   :keywords: amdgpu, ROCm, 内核驱动, 源码

##########
初探amdgpu
##########

amdgpu(ROCK-Kernel Driver)源码
======================================

拉取代码

.. code-block:: shell

    git clone --depth 1 https://github.com/ROCm/amdgpu.git

amd驱动代码目录

.. code-block:: shell

    ls drivers/gpu/drm/amd/

ROCT-Thunk-Interface 源码
=============================

rocm-systems项目中:

.. code-block:: shell
    
    # ioctl结构体定义
    cat rocm-systems/projects/rocr-runtime/libhsakmt/include/hsakmt/linux/kfd_ioctl.h
    # ioctl入口
    cat rocm-systems/projects/rocr-runtime/libhsakmt/src/libhsakmt.c

kmt全称Kernel Mode Thunk。

amdgpu简介
==========

参考 `AMD GPU Driver (amdgpu) 31.50.0 官方文档 <https://instinct.docs.amd.com/projects/amdgpu-docs/en/latest/index.html>`_。

AMD 当前官方仓库是 `ROCm/amdgpu <https://github.com/ROCm/amdgpu>`_，它是 ROCm 使用的 AMDGPU 内核源码分支；旧资料里的 ``ROCK-Kernel-Driver`` 可以视为它的历史名称/地址。

AMD GPU 驱动程序 (amdgpu) 是一款开源软件。它是软件生态系统（包括 ROCm 用户空间、AMD GPU 虚拟化和各类框架）中的关键组件，能够确保数据中心内强大的 AMD GPU 在 AI 和 HPC 应用负载下发挥最佳性能。

内核基础
==========

系统调用陷入
------------------

.. code-block:: 
    
    ┌──────────────────────────── 用户态 ring3 ────────────────────────────┐
    │  hipMalloc(&ptr, size)                                               │
    │    └─► libamdhip64 → libhsa-runtime64                                │
    │          └─► libhsakmt: hsaKmtAllocMemory(...)                       │
    │                └─► ioctl(kfd_fd, AMDKFD_IOC_ALLOC_MEMORY, &args)     │
    │                      │  glibc: rax=16, rdi=fd, rsi=cmd, rdx=&args    │
    │                      ▼ syscall 指令                                  │
    └──────────────────────│───────────────────────────────────────────────┘
                        │ 硬件: RCX←RIP, R11←RFLAGS, RIP←LSTAR, 切ring0
    ┌──────────────────────▼──────────────── 内核 ring0 ───────────────────┐
    │  arch/x86/entry/entry_64.S : entry_SYSCALL_64                        │
    │    swapgs → 切内核栈 → push pt_regs → call do_syscall_64              │
    │                          │                                           │
    │                          ▼                                           │
    │  do_syscall_64(): nr=16 → sys_call_table[16](regs)                   │
    │                          │                                           │
    │                          ▼                                           │
    │  __x64_sys_ioctl(regs): fd=regs->di, cmd=regs->si, arg=regs->dx      │
    │    └─► __se_sys_ioctl → fdget(fd) → struct file                      │
    │          └─► file->f_op->unlocked_ioctl(file, cmd, arg)              │
    │                          │  (函数指针，/dev/kfd 注册的是 kfd_ioctl)    │
    │                          ▼                                           │
    │  drivers/gpu/drm/amd/amdkfd/kfd_chardev.c : kfd_ioctl()              │
    │    └─► 按 cmd 查 kfd_ioctl_handlers[] 分发表                          │
    │          └─► kfd_ioctl_alloc_memory(file, cmd, args)  ← 第14周精读    │
    └──────────────────────────────────────────────────────────────────────┘


fd 与 struct file 的映射
--------------------------

files_struct 每个进程的打开文件表

.. code-block:: c

    struct files_struct {
        atomic_t                count;           // 引用计数（clone 时共享）
        struct fdtable          *fdt;            // 指向当前使用的 fdtable
        struct fdtable          fdtab;           // 内嵌默认的 fdtable（最多 64 个 fd）
        spinlock_t              file_lock;
        unsigned int            next_fd;         // 下次分配 fd 的起始搜索位置
        // ...
    };

fdtable 结构体

.. code-block:: c

    struct fdtable {
        unsigned int            max_fds;
        struct file __rcu       **fd;            // 核心！动态数组，fd 号就是下标
        struct file             **close_on_exec;
        // ...
    };

struct file 打开文件的内核对象

.. code-block:: c

    struct file {
        struct path             f_path;          // 包含 dentry + vfsmount
        struct inode            *f_inode;        // 底层 inode（设备文件对应 chardev inode）
        const struct file_operations *f_op;      // 关键！设备文件这里就是 kfd_fops
        spinlock_t              f_lock;
        atomic_long_t           f_count;         // 引用计数
        unsigned int            f_flags;         // O_RDWR, O_NONBLOCK 等
        fmode_t                 f_mode;
        struct mutex            f_pos_lock;
        loff_t                  f_pos;           // 文件偏移（设备文件通常不用）
        void                    *private_data;   // 极重要！驱动私有数据（kfd 进程指针等）
        // ... 很多其他字段
    };

open("/dev/kfd") 的完整链路


.. code-block:: text

    current -+ files
        |
        v
    struct files_struct
        |
        v
    struct fdtable
        |
        v
    fd[] 数组  ──索引──+  struct file *
                            |
                            +-- f_path.dentry   --+ /dev/kfd 的 dentry
                            +-- f_inode         --+ 设备 inode
                            +-- f_op            --+ kfd_fops
                            +-- private_data    --+ kfd_process（驱动私有的进程上下文）
                            +-- f_count         --+ 当前引用计数

file有关的概念结构

.. code-block:: text

    current-+files
        |
        v
    struct files_struct
        |
        v
    struct fdtable
        |
        v
    fd[] 数组  ──索引──+  struct file *
                            |
                            +-- f_path.dentry   --+ /dev/kfd 的 dentry
                            +-- f_inode         --+ 设备 inode
                            +-- f_op            --+ kfd_fops
                            +-- private_data    --+ kfd_process（驱动私有的进程上下文）
                            +-- f_count         --+ 当前引用计数


list_head 双向循环链表
--------------------------

.. code-block:: c

    struct list_head {
        struct list_head *next, *prev;
    };

