.. meta::
   :description: kfd_chardev.c源码初探, 浏览kfd字符设备初始化代码
   :keywords: linux, module, kfd, chardev

########################
kfd_chardev源码初探
########################

总览
==================================

目录： `drivers/gpu/drm/amd/amdkfd/kfd_chardev.c`

.. note:: 

    `vscode` 可使用 `ctrl+K+0` 折叠所有函数，方便浏览。

大体结构如下：

.. code-block:: c

    static long kfd_ioctl(struct file *, unsigned int, unsigned long);
    static int kfd_open(struct inode *, struct file *);
    static int kfd_release(struct inode *, struct file *);
    static int kfd_mmap(struct file *, struct vm_area_struct *);

    static const char kfd_dev_name[] = "kfd";

    static const struct file_operations kfd_fops = {
        .owner = THIS_MODULE,
        .unlocked_ioctl = kfd_ioctl,
        .compat_ioctl = compat_ptr_ioctl,
        .open = kfd_open,
        .release = kfd_release,
        .mmap = kfd_mmap,
    };

    static int kfd_char_dev_major = -1;
    struct device *kfd_device;
    static struct class kfd_class = {
        .name = kfd_dev_name,
    };

file_operations总览：

.. code-block:: text

                     /dev/kfd
                        |
            ┌───────────┼───────────┐
            |           |           |
        open        ioctl        mmap
            |           |           |
            v           v           v
    kfd_process     控制命令     特殊映射
            |           |           |
            |      ┌────┼────┐      |
            |      |    |    |      |
            |    Queue Memory Event |
            |                       |
            |                  Doorbell/MMIO
            |
        release
            |
            v
    kfd_unref_process()



module init/exit
============================

module init结构

.. code-block:: text

    module_init(amdgpu_init)
            │
            ▼
    amdgpu_init()
            │
            ├── amdgpu_sync_init()
            ├── ...
            │
            ├── amdgpu_amdkfd_init()
            │       │
            │       ▼
            │   kgd2kfd_init()
            │       │
            │       ▼
            │   kfd_init()
            │       │
            │       ├── 检查 KFD module 参数
            │       │
            │       ├── kfd_chardev_init()
            │       │       │
            │       │       ├── register_chrdev()
            │       │       │
            │       │       ├── class_register()
            │       │       │
            │       │       └── device_create()
            │       │
            │       ├── kfd_topology_init()
            │       │
            │       ├── kfd_process_create_wq()
            │       ├── kfd_procfs_init()
            │       └── kfd_debugfs_init()
            │
            └── pci_register_driver(&amdgpu_kms_pci_driver)

kfd_chardev_init()的结构可简化成：

.. code-block:: text

    kfd_chardev_init()
        │
        ├── register_chrdev()
        │       │
        │       └── 注册 file_operations
        │
        ├── class_register()
        │       │
        │       └── 创建 kfd device class
        │
        └── device_create()
                │
                └── 创建 kfd device
                        │
                        ▼
                     /dev/kfd

open/release
============================

建立和释放进程级 KFD 上下文。

kfd_open() 在用户进程打开 /dev/kfd 时执行。它主要做几件事：先检查 minor number，拒绝 32 位进程，然后调用 kfd_create_process(current) 获取或创建当前进程对应的 struct kfd_process，最后把它保存到：

.. code-block:: c

    filep->private_data = process;

kfd_release() 则对应关闭 /dev/kfd。它从 filep->private_data 取回 kfd_process，做必要的 notifier 清理，然后调用：

.. code-block:: c

    kfd_unref_process(process);

释放这个 fd 持有的 process 引用。

因此这一部分的核心作用是： **把 Linux process/file 和 KFD 的 kfd_process 生命周期关联起来。**


ioctl
============================

KFD 最主要的用户态控制接口。

这是整个 kfd_chardev.c 最核心、代码量最大的一部分。统一入口是：

.. code-block:: c

    static long kfd_ioctl(struct file *filep,unsigned int cmd, unsigned long arg)

它并不直接完成具体 GPU 操作，而是充当一个 dispatcher。主要流程是：   

.. code-block:: text

    userspace ioctl()
            ↓
    kfd_ioctl()
            ↓
    解析 ioctl number
            ↓
    查 amdkfd_ioctls[]
            ↓
    权限 / process 检查
            ↓
    copy_from_user()
            ↓
    kfd_ioctl_xxx()
            ↓
    copy_to_user()

这个文件最核心的设计其实是 ioctl dispatcher。它有一张 amdkfd_ioctls[] 表。

源码里会根据 ioctl number 从 amdkfd_ioctls[] 里找到具体 handler，然后执行对应函数。

这些 ioctl 大致可以分成几类：

.. code-block:: text

    Queue
    ├─ CREATE_QUEUE
    ├─ DESTROY_QUEUE
    ├─ UPDATE_QUEUE
    ├─ SET_CU_MASK
    └─ ALLOC_QUEUE_GWS

    Memory
    ├─ ALLOC_MEMORY_OF_GPU
    ├─ FREE_MEMORY_OF_GPU
    ├─ MAP_MEMORY_TO_GPU
    ├─ UNMAP_MEMORY_FROM_GPU
    └─ ACQUIRE_VM

    Event
    ├─ CREATE_EVENT
    ├─ DESTROY_EVENT
    ├─ SET_EVENT
    ├─ RESET_EVENT
    └─ WAIT_EVENTS

    Process / Device Info
    ├─ GET_VERSION
    ├─ GET_CLOCK_COUNTERS
    ├─ GET_PROCESS_APERTURES
    ├─ GET_AVAILABLE_MEMORY
    └─ GET_TILE_CONFIG

    Debug / Runtime
    ├─ RUNTIME_ENABLE
    ├─ SET_DEBUG_TRAP
    ├─ PC_SAMPLE
    └─ ...

所以 ioctl 这部分可以理解成： **ROCm/HSA Runtime 向 KFD 发出“创建队列、分配显存、映射内存、等待事件、调试”等控制命令的主要通道。**

mmap
============================

把特殊 GPU 资源映射到用户态。

kfd_mmap() 主要不是用来映射普通 GPU buffer，而是映射一些特殊 KFD 资源。

入口首先从：

.. code-block:: c

    filep->private_data

找到当前 kfd_process，然后从：

.. code-block:: c

    vma->vm_pgoff

解码出：

.. code-block:: c

    mmap type
    gpu_id

接着根据不同 mmap type 分发。
当前主要支持两类: KFD_MMAP_TYPE_DOORBELL和KFD_MMAP_TYPE_MMIO。
还有一些旧类型已经明确不支持：KFD_MMAP_TYPE_EVENTS和KFD_MMAP_TYPE_RESERVED_MEM

Doorbell
------------------

.. code-block:: c

    KFD_MMAP_TYPE_DOORBELL


调用：

.. code-block:: c

    kfd_doorbell_mmap(...)

把 GPU doorbell page 映射到用户空间。
这非常重要，因为用户态 queue 提交 packet 后，可以直接写 doorbell：

.. code-block:: c

    Userspace
    |
    | write doorbell
    v
    MMIO / doorbell page
    |
    v
    GPU 知道 queue 有新任务

MMIO
------------------

.. code-block:: c

    KFD_MMAP_TYPE_MMIO

调用：

.. code-block:: c
    
    kfd_mmio_mmap(...)

内部通过：

.. code-block:: c

    io_remap_pfn_range()

把特定 GPU MMIO page 映射到用户态。

所以 mmap 这一部分可以概括为： **给用户态建立到 KFD 特殊硬件资源的直接映射，尤其是 doorbell。**
