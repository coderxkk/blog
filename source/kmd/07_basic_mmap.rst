.. meta::
   :description: 打通用户态与内核态的内存共享,围绕 VMA、页表和地址映射，实现双方读写同一物理页。
   :keywords: mmap, vma, PA, VA, page tables

########################
理解mmap
########################

基础概念
==================================

VA、PA、PFN
---------------------------

.. list-table:: 内存地址概念
   :header-rows: 1
   :widths: 20 20 20

   * - 名称
     - 示例值
     - 含义
   * - 用户虚拟地址 U
     - 0x70000000
     - 用户程序访问这一页的起点
   * - 内核虚拟地址 K
     - 用 K 表示
     - 驱动访问同一页的起点
   * - 物理地址 P
     - 0x12345000
     - 这一物理页的起点
   * - 页帧号 PFN
     - 0x12345
     - 该物理页的编号

VMA和页表
------------------------------

VMA 描述“一段虚拟地址的范围、规则和管理状态”。

页表记录具体映射与硬件访问权限。

两者配合，让程序能正确访问内存。

.. list-table:: VMA vs 页表
   :header-rows: 1
   :widths: 20 20 20

   * - 描述对象
     - 一段虚拟地址范围
     - 按页组织的映射
   * - 主要内容
     - 范围、访问规则、关联文件、处理回调
     - 物理页映射、有效状态、硬件权限等
   * - 主要使用者
     - 内核内存管理代码
     - 硬件地址翻译机制，以及维护它的内核代码


通过缺页异常，将VMA与页表连接起来。假设 VMA 已经存在，但目标页尚未建立有效映射。用户执行：

.. code-block:: c

   u[8] = 42;

在常见的按需映射路径中，会发生：

.. code-block:: text

   CPU 尝试写入虚拟地址
         ↓
   硬件发现缺少可用映射，触发异常
         ↓
   内核查找该地址对应的 VMA，并检查访问规则
         ↓
   按映射类型准备页面、建立映射
         ↓
   异常处理成功后，重新执行原来的写入指令

vm_area_struct
------------------------------------

官方注释：

.. note:: 

   这个结构体描述一个虚拟内存区域。任务地址空间中的每个虚拟内存区域，都有对应的描述对象。

   虚拟内存区域是进程虚拟地址空间的一部分，缺页处理程序对它采用特定的处理规则，例如共享库区域、可执行代码区域等。

   在获取稳定引用之前，RCU 读者只能访问明确标记允许访问的字段。

   添加新成员时，必须更新 vm_area_init_from()，确保复制 VMA 内容时也复制这些成员。

这里的“每个区域一个对象”，不是每个进程只有一个 VMA。一个进程通常有很多 VMA；共享同一个 mm_struct 的线程也共享这套地址空间。

RCU 是一种并发访问机制。这里的限制提醒我们：拿到一个 VMA 指针，并不意味着可以不加保护地读取所有字段。

举个例子：

.. code-block:: text

   范围：[0x70000000, 0x70001000)

   规则：允许读、允许写、共享映射

   来源：某个设备文件

.. list-table:: vm_area_struct重要字段说明
   :header-rows: 1
   :widths: 20 20 20

   * - 字段
     - 要回答的问题
     - 本例中的理解
   * - vm_start
     - 用户虚拟地址范围从哪里开始？
     - 0x70000000
   * - vm_end
     - 范围在哪里结束？
     - `0x70001000`，不包含该地址
   * - vm_pgoff
     - 映射对象从哪个页偏移开始？
     - 单位是页
   * - vm_flags
     - 内核如何管理这段映射？
     - 读写、共享等规则
   * - vm_page_prot
     - 建立页表映射时使用什么保护属性？
     - 架构相关的权限、缓存属性等
   * - vm_ops
     - 对该 VMA 的特定操作由谁处理？
     - 可以提供 `.fault`、`.open`、`.close` 等回调
   * - vm_private_data
     - 
     - 回调如何找到驱动自己的上下文
   * - vm_file
     - 
     - 关联哪个文件或设备
   * - vm_mm
     - 
     - 所属的进程地址空间

remap_pfn_range函数
-------------------------------------------------

作用：把 **一段连续物理页（用 PFN 页帧号描述）** ，直接映射到用户进程虚拟地址空间（VMA），在驱动 ``mmap`` 回调里最常用。

``remap_pfn_range()`` 是 Linux 内核提供的 **主动建立页表** 函数，位于 ``mm/memory.c`` ，头文件 ``<linux/mm.h>`` 。

.. code-block:: c

   int remap_pfn_range(struct vm_area_struct *vma,
        unsigned long addr,
        unsigned long pfn,
        unsigned long size,
        pgprot_t prot);

**参数详解**

1. **vma** ： ``struct vm_area_struct *``，用户进程调用 ``mmap()`` 后内核分配的虚拟内存区域。驱动 ``file_operations->mmap`` 回调入参自带这个 vma。
2. **addr** ：用户虚拟地址 **起始地址** ，一般直接填 ``vma->vm_start``，必须页对齐。
3. **pfn** ：物理内存 **起始页帧号** 。
   - ``pfn = phys_addr >> PAGE_SHIFT``；物理地址右移 PAGE_SHIFT 得到 PFN
   - 不是物理地址！这点很容易踩坑
4. **size** ：映射字节长度，内部会自动 ``PAGE_ALIGN``，建议传入页对齐值。
5. **prot** ：页保护属性 ``pgprot_t``，一般用 ``vma->vm_page_prot`` ；设备寄存器区域要禁用缓存。

**核心原理**

1. 从 ``vma->vm_mm`` 获取进程的内存描述符 ``mm_struct`` ；
2. 从 ``addr`` 开始逐级遍历页表：PGD → PUD → PMD → PTE， **预先创建页表项** ；
3. PTE 直接填入传入的 PFN，设置权限 prot；
4. 刷缓存 / TLB；
5. 设置 VMA 标记： ``VM_IO | VM_PFNMAP | VM_DONTEXPAND | VM_DONTDUMP`` ， **告诉内核：这不是普通 page，不要做 page fault、不要 swap、不要统计页引用计数** 。

.. warning::

   ⚠️ 区别于缺页式映射（nopage /fault handler）：
   remap_pfn_range 是 **一次性全部建好页表** ；访问内存不会触发缺页异常。

**典型使用场景（驱动 mmap）**

1. 映射 MMIO 设备寄存器空间（framebuffer、PCI BAR、SOC 外设寄存器）
2. 映射 DMA 物理缓冲区（ ``dma_alloc_coherent`` 分配的物理连续内存）
3. /dev/mem，把物理内存直接暴露给用户态
4. 内核预留物理内存，零拷贝给用户空间

**重要坑点 & 约束 **

1. **只能映射连续物理页** ；物理不连续不能一次性调用，需要循环多次 remap。
2. **VM_PFNMAP 映射，内核不持有 page 引用计数** ：
   - 不能对这些页面调用 ``get_page()`` / ``put_page()`` ；
   - 内核不会自动保护，驱动必须自己保证物理内存生命周期，用户态 munmap 不会释放物理内存。
3. **禁止 COW** ：如果 VMA 是可写且允许写时复制，调用会失败。
4. MMIO 寄存器映射：prot 需要去掉缓存（ ``pgprot_noncached`` ），否则 CPU 缓存会导致寄存器读写异常。
5. 不要用它映射普通 ``kmalloc`` 内存： ``kmalloc`` 得到的内核虚拟地址对应的物理页是系统可回收 page，PFN mapping 会破坏 page 管理。
   - 内核普通内存映射到用户态，优先用 ``vm_insert_page()`` 。
6. 配套封装： ``io_remap_pfn_range()`` ，早期内核是独立实现，现代内核很多架构上等价于 remap_pfn_range； ``vm_iomap_memory()`` 是更推荐的 MMIO 高层封装。

vm_insert_page vs remap_pfn_range
--------------------------------------------------

.. list-table:: vm_insert_page 与 remap_pfn_range 对比
   :header-rows: 1
   :widths: 14 36 40

   * - 项目
     - vm_insert_page
     - remap_pfn_range
   * - 输入
     - ``struct page*``
     - 起始 PFN + size
   * - VMA 标记
     - ``VM_MIXEDMAP``
     - ``VM_PFNMAP``
   * - page refcount
     - ✅ 自动 get/put，内核正常管理
     - ❌ 完全不维护 refcount
   * - 映射粒度
     - 单页，循环调用支持离散页
     - 一次性批量，必须物理连续
   * - 页保护 prot
     - 复用 ``vma->vm_page_prot``，不可单独指定
     - 可单独传入 ``pgprot_t``
   * - COW/swap
     - 支持
     - ❌ 禁止 COW，不 swap
   * - 适用对象
     - buddy 分配普通内存
     - MMIO、连续 DMA 物理内存


源码阅读
=========================

mmap完整调用栈
--------------------------

.. code-block:: text

   用户态
   └─ libc mmap() 包装函数（不在内核仓库）
         └─ syscall(SYS_mmap, ...) 或 mmap_pgoff

   内核态
   └─ SYSCALL_DEFINE6(mmap, ...)          [arch/x86/kernel/sys_x86_64.c]
         │  检查 offset 页对齐；字节偏移转为页偏移
         └─ ksys_mmap_pgoff()               [mm/mmap.c]
               │  根据 fd 获取 struct file
               └─ vm_mmap_pgoff()            [mm/util.c]
                  │  获取 mmap_lock 写锁
                  └─ do_mmap()             [mm/mmap.c]
                        │  检查参数、计算 VMA 标志、选择虚拟地址范围
                        └─ mmap_region() 或 __mmap_region()   [mm/mmap.c]
                              │  准备 VMA，进入文件/驱动映射回调
                              │
                              ├─ ① 尝试合并相邻 VMA（vma_merge 等分支）
                              │     └─ 若可合并，可能不分配新 VMA，直接扩展后跳至 file_expanded
                              │
                              ├─ ② 若无法合并，走 cannot_expand 路径：
                              │     ├─ vm_area_alloc()          分配 VMA 对象
                              │     ├─ vma_set_range()          设置边界和偏移
                              │     ├─ vm_flags_init()          初始化标志
                              │     ├─ vm_get_page_prot()       设置保护属性
                              │     │
                              │     ├─ 若为文件映射：
                              │     │    ├─ vma->vm_file = get_file(file)
                              │     │    └─ mmap_file()          [mm/internal.h]
                              │     │         │  包装回调调用并处理失败
                              │     │         └─ call_mmap()     [include/linux/fs.h]
                              │     │              └─ file->f_op->mmap(file, vma)   ← 驱动 mmap 回调
                              │     │
                              │     └─ 若为匿名映射：
                              │          └─ shmem_zero_setup() 或 vma_set_anonymous()
                              │
                              └─ ③ 回调成功后：
                                 ├─ vma_iter_store()        将 VMA 纳入地址空间管理
                                 └─ vma_link_file() 等后续


fault(硬件缺页异常)调用栈
------------------------------------

.. code-block:: text

   用户态
   └─ p[0] = 42                         ← 用户指令，写共享映射地址
         │
         │  CPU 查页表，发现 PTE 不存在 / 权限不足
         │  → 触发 #PF（缺页异常），保存用户现场，跳入内核
         ▼
   内核态：缺页异常入口（arch/x86/mm/fault.c）
   └─ exc_page_fault()
         │  取得故障地址：传统 x86 从 CR2 读取
         └─ handle_page_fault()
               │  区分用户地址 / 内核地址
               └─ do_user_addr_fault()          ← 用户地址分支
                  │
                  │  查找并保护 VMA、检查访问权限
                  │  搜索点：
                  │    lock_vma_under_rcu      快速路径，RCU 下查找 VMA
                  │    lock_mm_and_find_vma    慢速路径，加锁查找 VMA
                  │    access_error()          判断访问是否违反 VMA 权限
                  │    （前两者是不同查找/加锁路径，不是顺序执行）
                  │
                  └─ handle_mm_fault()        [mm/memory.c]
                        │
                        └─ __handle_mm_fault()
                              │
                              └─ handle_pte_fault()
                                 │
                                 │  PTE 不存在 → 进入缺页处理
                                 ▼
                              do_pte_missing()
                                 │
                                 │  文件/共享映射缺页 → do_fault()
                                 │  （普通匿名缺页走 do_anonymous_page()，不在此路径）
                                 ▼
                              do_fault()
                                 │
                                 │  按访问类型分派：
                                 │    读缺页            → do_read_fault()
                                 │    私有映射写缺页    → do_cow_fault()
                                 │    共享映射写缺页    → do_shared_fault()   ← 本例
                                 ▼
                              do_shared_fault()
                                 │
                                 └─ __do_fault()
                                       │
                                       │  最关键一行：
                                       │    ret = vma->vm_ops->fault(vmf);
                                       ▼
                              uio_vma_fault()          ← 驱动提供的 fault 回调
                                 │
                                 │  从 vm_private_data 找到设备上下文
                                 │  计算对应页面
                                 │  get_page(page);
                                 │  vmf->page = page;    ← 把页面交给核心缺页代码
                                 │                        （此时尚未安装 PTE）
                                 ▼
                              回调成功返回，继续普通页路径：
                              do_shared_fault()
                                 │
                                 └─ finish_fault()
                                       │  完成映射前检查和页表操作
                                       ▼
                                 set_pte_range()
                                       │  构造并安装 PTE
                                       ▼
                                 页表映射完成


缺页异常返回用户态调用栈
--------------------------------------

.. code-block:: text

   异常处理逐层返回
   └─ 传统 x86-64 IDT 路径底层返回代码（arch/x86/entry/entry_64.S）
         │  搜索点：
         │    swapgs_restore_regs_and_return_to_usermode
         │    native_irq_return_iret
         │    iretq
         │
         │  恢复保存的用户执行现场
         ▼
   用户态
   └─ CPU 重新执行故障指令：p[0] = 42
         │  此时 PTE 已建立，写入成功
         ▼
      继续执行后续用户代码