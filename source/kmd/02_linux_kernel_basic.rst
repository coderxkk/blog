.. meta::
   :description: linux内核开发的基础知识
   :keywords: linux, module, basic

########################
Linux内核基础知识
########################

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


container_of
--------------------------

通过结构体成员的指针，获取包含它的结构体的指针。

示例：

.. code-block:: c

    struct person {
        int age;
        char name[20];
    };
    struct person p;
    int *age_ptr = &p.age;
    struct person *p_ptr = container_of(age_ptr, struct person, age);
    // p_ptr == &p


ftrace基础
--------------------------

ftrace = **framework tracing**，是 **内核自带的、不需要装任何额外软件** 的追踪框架，通过一个叫 tracefs 的伪文件系统暴露成一堆文件，你 `echo` 写控制文件、 `cat` 读结果文件，本质就是在和内核里的追踪器对话。

ftrace基本用法：

实验 1：function 全量追踪，感受一下（10 秒就够）

.. code-block:: shell

    cd /sys/kernel/debug/tracing
    echo nop > current_tracer; echo > trace
    echo function > current_tracer
    echo 1 > tracing_on
    timeout 3 cat trace_pipe        # 看3秒就 Ctrl+C / timeout 自动停
    echo 0 > tracing_on; echo nop > current_tracer

你会看到洪水般的输出，先学会读每一列（文件头注释本身就是图例）：

.. code-block:: text

    #           TASK-PID     CPU#  ||||   TIMESTAMP  FUNCTION
    #              | |         |   ||||      |         |
            bash-1234  [000] .... 12345.678901: mutex_unlock <-__alloc_fd
            进程名-PID   哪个CPU  标志位  时间戳(秒)   被调函数 <-调用者


三种内核调试手段：

.. code-block:: text

    pr_info/printk   ：你要提前在代码里写死打印，改一次重编一次，适合自己的模块
    ftrace           ：不用改代码！动态追踪内核里几乎任意函数，开关即生效，适合看现成内核/KFD
    kprobe/eBPF      ：更灵活，能在任意指令地址埋点、读参数（后面进阶再学）

ftrace实现原理

.. code-block:: text

    ① 编译期：
        内核用 -pg/-fentry 编译，几乎每个函数入口都埋一条 5 字节占位指令
        (正常运行时被替换成 nop，所以没开追踪时开销≈0)

    ② 开启 function tracer：
        内核用 stop_machine 在所有 CPU 上把 nop 动态改写成 call ftrace_caller
        （不需要重新编译内核！这就是"动态 ftrace / DYNAMIC_FTRACE"）

    ③ 被追踪函数被调用时：
        函数入口 → ftrace 回调 → 把"谁在哪个CPU上调用了谁"写入 per-CPU 环形缓冲区(ring buffer)

    ④ 用户态：
        cat trace        = 读 ring buffer 当前快照
        cat trace_pipe   = 流式读，来一条读走一条


强烈建议同时学会 trace-cmd（计划里点名的工具）

直接 echo 文件适合理解原理， **真实干活用** `trace-cmd` **前端**，一条命令完成 "过滤 - 录制 - 绑定进程 - 停止 - 保存"：

.. code-block:: shell

    sudo apt install trace-cmd

    # 录制：function_graph  tracer，只看 ioctl 入口及其子调用，追踪 ./ioctl_test 的生命周期
    sudo trace-cmd record -p function_graph -g __x64_sys_ioctl ./ioctl_test
    # 录完生成 trace.dat，离线慢慢看，不刷屏
    sudo trace-cmd report | less
