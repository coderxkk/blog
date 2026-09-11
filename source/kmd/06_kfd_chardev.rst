.. meta::
   :description: kfd_chardev.c源码初探, 浏览kfd字符设备初始化代码
   :keywords: linux, module, kfd, chardev

########################
kfd_chardev源码初探
########################

基础
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

    