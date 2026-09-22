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


mmap部分
---------------------------

usermode测试用例
---------------------------











