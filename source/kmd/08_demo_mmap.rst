.. meta::
   :description: mmap demo练习
   :keywords: mmap, vma, PA, VA, page tables

########################
mmap用例练习
########################

demo
==================================

mmap简单普通页demo
---------------------------

mmap_simple.c
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    // SPDX-License-Identifier: GPL-2.0-only
    /* 教学用：Linux 5.15，一次只运行一个用户程序。 */
    #include <linux/module.h>
    #include <linux/fs.h>
    #include <linux/miscdevice.h>
    #include <linux/mm.h>
    #include <linux/highmem.h>
    #include <linux/ioctl.h>

    #define CMD_CHANGE _IO('m', 1)

    static struct page *shared_page;
    static int *kernel_ptr;

    /* 用户调用 mmap 时，内核进入这里。 */
    static int demo_mmap(struct file *file, struct vm_area_struct *vma)
    {
        if (vma->vm_end - vma->vm_start != PAGE_SIZE ||
            vma->vm_pgoff != 0 || !(vma->vm_flags & VM_SHARED))
            return -EINVAL;

        /* Linux 5.15 的写法：禁止扩展映射。 */
        vma->vm_flags |= VM_DONTEXPAND;
        return vm_insert_page(vma, vma->vm_start, shared_page);
    }

    /* ioctl 只是通知内核：现在来读这页，然后修改它。 */
    static long demo_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
    {
        int value;

        if (cmd != CMD_CHANGE)
            return -ENOTTY;
        value = READ_ONCE(*kernel_ptr);
        pr_info("mmap_simple: kernel read %d\n", value);
        if (value != 200)
            return -EINVAL;
        WRITE_ONCE(*kernel_ptr, 300);
        pr_info("mmap_simple: kernel wrote 300\n");
        return 0;
    }

    static const struct file_operations demo_fops = {
        .owner = THIS_MODULE,
        .mmap = demo_mmap,
        .unlocked_ioctl = demo_ioctl,
    };

    /* miscdevice 是注册简单字符设备的一种便捷方式。 */
    static struct miscdevice demo_device = {
        .minor = MISC_DYNAMIC_MINOR,
        .name = "mmap_simple",
        .fops = &demo_fops,
        .mode = 0600,
    };

    static int __init demo_init(void)
    {
        int ret;

        /* 分配并清零一页，再通过内核地址写入 100。 */
        shared_page = alloc_page(GFP_KERNEL | __GFP_ZERO);
        if (!shared_page)
            return -ENOMEM;
        kernel_ptr = page_address(shared_page);
        *kernel_ptr = 100;
        ret = misc_register(&demo_device);
        if (ret)
            put_page(shared_page);
        return ret;
    }

    static void __exit demo_exit(void)
    {
        misc_deregister(&demo_device);
        put_page(shared_page);
    }

    module_init(demo_init);
    module_exit(demo_exit);
    MODULE_LICENSE("GPL");

user.c
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    #include <stdio.h>
    #include <fcntl.h>
    #include <unistd.h>
    #include <sys/mman.h>
    #include <sys/ioctl.h>

    /* 与驱动中的命令一致；ioctl 不传递数值，只触发操作。 */
    #define CMD_CHANGE _IO('m', 1)

    int main(void)
    {
        long size = sysconf(_SC_PAGESIZE);
        int fd, result = 1;
        void *address;
        volatile int *p;

        if (size <= 0)
            return 1;
        fd = open("/dev/mmap_simple", O_RDWR);
        if (fd < 0) {
            perror("open");
            return 1;
        }
        address = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (address == MAP_FAILED) {
            perror("mmap");
            close(fd);
            return 1;
        }
        p = address;

        /* 核心实验从这里开始。 */
        printf("1. user read: %d (expected 100)\n", *p);
        if (*p != 100) {
            fprintf(stderr, "Reload the module to reset the page to 100.\n");
            goto out;
        }
        *p = 200;
        puts("2. user wrote: 200");
        if (ioctl(fd, CMD_CHANGE) < 0) {
            perror("ioctl");
            goto out;
        }
        printf("3. user read: %d (expected 300)\n", *p);
        if (*p == 300) {
            puts("PASS");
            result = 0;
        }

    out:
        if (munmap(address, size) < 0) {
            perror("munmap");
            result = 1;
        }
        if (close(fd) < 0) {
            perror("close");
            result = 1;
        }
        return result;
    }


mmap pci的简单demo
---------------------------

pci_mmap_demo.c
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    // SPDX-License-Identifier: GPL-2.0-only
    /* Linux 5.15 / x86_64，QEMU 中只添加一个 EDU 设备，不做热拔插。 */
    #include <linux/module.h>
    #include <linux/pci.h>
    #include <linux/fs.h>
    #include <linux/miscdevice.h>
    #include <linux/mm.h>
    #include <linux/mutex.h>

    static resource_size_t bar0_start;
    static bool ready;
    static DEFINE_MUTEX(device_lock);

    /* 加载时选择：0 = 立即映射；1 = 首次访问时通过 fault 映射。 */
    static bool use_fault;
    module_param(use_fault, bool, 0444);
    MODULE_PARM_DESC(use_fault, "0: remap_pfn_range; 1: on-demand PFN fault");

    /* 只有缺页模式使用这个回调；它处理的是 BAR 的 PFN，不是普通 RAM 页。 */
    static vm_fault_t demo_fault(struct vm_fault *vmf)
    {
        vm_fault_t ret = VM_FAULT_SIGBUS;

        /* 本例只映射 BAR0 第一页：页偏移只能为 0。 */
        if (vmf->pgoff != 0)
            return VM_FAULT_SIGBUS;
        mutex_lock(&device_lock);
        if (ready) {
            ret = vmf_insert_pfn(vmf->vma, vmf->address,
                        bar0_start >> PAGE_SHIFT);
            pr_info("pci_mmap_demo: fault: insert BAR0 PFN, result=0x%x\n",
                (unsigned int)ret);
        }
        mutex_unlock(&device_lock);
        /* 直接返回 vm_fault_t；不能把它当作普通的 0/-errno。 */
        return ret;
    }

    static const struct vm_operations_struct demo_vm_ops = {
        .fault = demo_fault,
    };

    /* 用户 mmap：立即建立映射，或只登记缺页处理方法。 */
    static int demo_mmap(struct file *file, struct vm_area_struct *vma)
    {
        int ret = -ENODEV;

        if (vma->vm_end - vma->vm_start != PAGE_SIZE ||
            vma->vm_pgoff != 0 || !(vma->vm_flags & VM_SHARED))
            return -EINVAL;
        if (vma->vm_flags & VM_EXEC)
            return -EACCES;

        /* 寄存器空间使用非缓存映射；这是 Linux 5.15 的标志写法。 */
        /* MMIO 不使用普通 RAM 的加密属性，与 io_remap_pfn_range 一致。 */
        vma->vm_page_prot = pgprot_decrypted(pgprot_noncached(vma->vm_page_prot));
        vma->vm_flags |= VM_IO | VM_DONTEXPAND | VM_DONTDUMP;
        vma->vm_flags &= ~VM_MAYEXEC;
        mutex_lock(&device_lock);
        if (ready) {
            if (use_fault) {
                /* 暂不填充页表；vmf_insert_pfn 要求预先设置 VM_PFNMAP。 */
                vma->vm_flags |= VM_PFNMAP;
                vma->vm_ops = &demo_vm_ops;
                ret = 0;
                pr_info("pci_mmap_demo: mmap: deferred, waiting for access\n");
            } else {
                /* PFN = CPU 物理资源地址 >> PAGE_SHIFT。 */
                ret = remap_pfn_range(vma, vma->vm_start,
                            bar0_start >> PAGE_SHIFT,
                            PAGE_SIZE, vma->vm_page_prot);
                if (!ret)
                    pr_info("pci_mmap_demo: mmap: remap_pfn_range done\n");
            }
        }
        mutex_unlock(&device_lock);
        return ret;
    }

    static const struct file_operations demo_fops = {
        .owner = THIS_MODULE,
        .mmap = demo_mmap,
    };

    static struct miscdevice demo_device = {
        .minor = MISC_DYNAMIC_MINOR,
        .name = "pci_mmap_demo",
        .fops = &demo_fops,
        .mode = 0600,
    };

    /* PCI ID 匹配后，内核调用 probe；此时设备还没有用户映射。 */
    static int demo_probe(struct pci_dev *pdev, const struct pci_device_id *id)
    {
        int ret;

        mutex_lock(&device_lock);
        if (ready) { /* 本例只支持一个设备。 */
            ret = -EBUSY;
            goto unlock;
        }
        ret = pci_enable_device_mem(pdev);
        if (ret)
            goto unlock;
        if (!(pci_resource_flags(pdev, 0) & IORESOURCE_MEM) ||
            pci_resource_len(pdev, 0) < PAGE_SIZE ||
            !IS_ALIGNED(pci_resource_start(pdev, 0), PAGE_SIZE)) {
            ret = -EINVAL;
            goto disable;
        }
        /* 声明驱动占用 BAR0，避免与其他驱动同时使用。 */
        ret = pci_request_region(pdev, 0, "pci_mmap_demo");
        if (ret)
            goto disable;
        bar0_start = pci_resource_start(pdev, 0);
        ret = misc_register(&demo_device);
        if (ret)
            goto release;
        ready = true;
        dev_info(&pdev->dev, "BAR0=%pa; created /dev/pci_mmap_demo\n", &bar0_start);
        mutex_unlock(&device_lock);
        return 0;

    release:
        pci_release_region(pdev, 0);
    disable:
        pci_disable_device(pdev);
    unlock:
        mutex_unlock(&device_lock);
        return ret;
    }

    static void demo_remove(struct pci_dev *pdev)
    {
        mutex_lock(&device_lock);
        ready = false;
        misc_deregister(&demo_device);
        pci_release_region(pdev, 0);
        pci_disable_device(pdev);
        mutex_unlock(&device_lock);
    }

    static const struct pci_device_id demo_ids[] = {
        { PCI_DEVICE(0x1234, 0x11e8) }, /* QEMU EDU 的厂商 ID 和设备 ID */
        { }
    };
    MODULE_DEVICE_TABLE(pci, demo_ids);

    static struct pci_driver demo_driver = {
        .name = "pci_mmap_demo",
        .id_table = demo_ids,
        .probe = demo_probe,
        .remove = demo_remove,
        .driver = { .suppress_bind_attrs = true }, /* 不提供手动 bind/unbind 接口 */
    };

    /* 自动生成注册和注销 PCI 驱动的模块入口。 */
    module_pci_driver(demo_driver);
    MODULE_LICENSE("GPL");

user.c
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    #include <stdio.h>
    #include <stdint.h>
    #include <inttypes.h>
    #include <fcntl.h>
    #include <unistd.h>
    #include <sys/mman.h>

    #ifndef __x86_64__
    #error "This teaching demo targets an x86_64 QEMU guest."
    #endif

    int main(void)
    {
        long size = sysconf(_SC_PAGESIZE);
        int fd, result = 1;
        void *address;
        volatile uint32_t *regs;
        uint32_t written = 0x12345678, received;

        if (size <= 0)
            return 1;
        fd = open("/dev/pci_mmap_demo", O_RDWR);
        if (fd < 0) {
            perror("open");
            return 1;
        }
        address = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (address == MAP_FAILED) {
            perror("mmap");
            close(fd);
            return 1;
        }
        regs = address;

        puts("mmap returned; about to access BAR0 for the first time");
        fflush(stdout);
        /* 每个 uint32_t 占 4 字节：regs[1] 对应 BAR0 + 0x04。 */
        printf("Device ID register: 0x%08" PRIx32 "\n", regs[0]);
        regs[1] = written;
        received = regs[1];
        printf("Wrote: 0x%08" PRIx32 "\n", written);
        printf("Read:  0x%08" PRIx32 " (expected 0x%08" PRIx32 ")\n",
            received, (uint32_t)~written);
        if (received == (uint32_t)~written) {
            puts("PASS: PCI BAR mmap works");
            result = 0;
        }
        if (munmap(address, size) < 0) {
            perror("munmap");
            result = 1;
        }
        if (close(fd) < 0) {
            perror("close");
            result = 1;
        }
        return result;
    }












