.. meta::
   :description: 字符设备驱动开发基础知识
   :keywords: linux, module, 编译

########################
字符设备驱动
########################

极简字符设备驱动：/dev/my_dev
==================================

代码
--------------------------

.. code-block:: c

    #include <linux/module.h>
    #include <linux/fs.h>
    #include <linux/cdev.h>
    #include <linux/uaccess.h>
    #include <linux/slab.h>
    #include <linux/device.h>

    #define MY_DEV_NAME "my_dev"
    /* 内核内部缓冲区大小 */
    #define MY_BUF_SIZE 256

    static dev_t my_dev_no;
    static struct cdev my_cdev;
    static struct class *my_class;

    /* 全局内核缓冲区，极简版本；真实驱动每个open应该分配**每个进程私有缓冲区**，参考KFD kfd_process */
    static char my_kbuf[MY_BUF_SIZE];
    static size_t my_buf_len;  /* 当前有效数据长度 */

    /* open: 用户态 open("/dev/my_dev") 触发
    * KFD kfd_open：每次open，alloc kfd_process，绑定到当前task；
    * 这里极简：只打印；改进版应该每个open分配私有内核对象，不要用全局buf
    */
    static int my_dev_open(struct inode *inode, struct file *file)
    {
        pr_info("my_dev: open() called, pid=%d\n", current->pid);

        /* 进阶模仿KFD：open的时候分配一个内核对象，挂到 file->private_data
        * struct my_process *kp = kzalloc(sizeof(*kp), GFP_KERNEL);
        * file->private_data = kp;
        * KFD 就是 file->private_data = kfd_process;
        */
        return 0;
    }

    /* release: close(fd) 触发，进程退出自动close也会走
    * KFD kfd_release：销毁 kfd_process 对象，清理资源
    */
    static int my_dev_release(struct inode *inode, struct file *file)
    {
        pr_info("my_dev: release() called, pid=%d\n", current->pid);

        /* KFD 在这里 kfree(file->private_data); 释放每个进程的内核对象 */
        return 0;
    }

    /* read：用户 read(fd, buf, count)
    * arg: file, 用户态buf(__user!), 用户请求读取count, offset
    * 返回值：>0 实际读到字节；0 到达EOF；负数负errno
    * 禁止直接 user_buf[i]！必须 copy_to_user
    */
    static ssize_t my_dev_read(struct file *file, char __user *user_buf,
                            size_t count, loff_t *offset)
    {
        size_t to_read;
        int ret;

        pr_info("my_dev: read() count=%zu offset=%lld\n", count, *offset);

        if (*offset >= my_buf_len) {
            return 0; /* EOF，cat读到0就停止 */
        }

        to_read = min(count, my_buf_len - (size_t)*offset);

        /* copy_to_user: 内核 -> 用户空间；失败返回未拷贝字节数 */
        ret = copy_to_user(user_buf, my_kbuf + *offset, to_read);
        if (ret) {
            pr_err("my_dev: copy_to_user fail\n");
            return -EFAULT;
        }

        *offset += to_read;
        return to_read; /* 返回实际读走多少字节，不能返回0！ */
    }

    /* write：用户 write(fd, buf, count)
    * copy_from_user：用户空间 -> 内核空间；禁止直接访问 user_buf
    */
    static ssize_t my_dev_write(struct file *file, const char __user *user_buf,
                                size_t count, loff_t *offset)
    {
        size_t to_write;
        int ret;

        pr_info("my_dev: write() count=%zu offset=%lld\n", count, *offset);

        to_write = min(count, (size_t)MY_BUF_SIZE - 1);
        if (to_write == 0)
            return -ENOSPC;

        ret = copy_from_user(my_kbuf, user_buf, to_write);
        if (ret) {
            pr_err("my_dev: copy_from_user fail\n");
            return -EFAULT;
        }

        my_kbuf[to_write] = '\0';
        my_buf_len = to_write;
        *offset += to_write;

        return to_write; /* 返回实际写入字节，echo依赖返回值 */
    }

    /* 文件操作表，对标 KFD kfd_fops */
    static const struct file_operations my_dev_fops = {
        .owner   = THIS_MODULE,
        .open    = my_dev_open,
        .release = my_dev_release,
        .read    = my_dev_read,
        .write   = my_dev_write,
    };

    static int __init my_dev_init(void)
    {
        int err;
        struct device *dev;

        /* 1. 申请设备号 */
        err = alloc_chrdev_region(&my_dev_no, 0, 1, MY_DEV_NAME);
        if (err < 0) {
            pr_err("alloc_chrdev_region failed %d\n", err);
            return err;
        }
        pr_info("my_dev: major=%d minor=%d\n", MAJOR(my_dev_no), MINOR(my_dev_no));

        /* 2. cdev初始化，绑定 fops */
        cdev_init(&my_cdev, &my_dev_fops);
        my_cdev.owner = THIS_MODULE;

        /* 3. 添加cdev到内核 */
        err = cdev_add(&my_cdev, my_dev_no, 1);
        if (err) {
            pr_err("cdev_add failed\n");
            unregister_chrdev_region(my_dev_no, 1);
            return err;
        }

        /* 4. 创建class，自动生成 /dev/my_dev，不需要手动mknod */
        my_class = class_create(THIS_MODULE, "my_class");
        if (IS_ERR(my_class)) {
            err = PTR_ERR(my_class);
            cdev_del(&my_cdev);
            unregister_chrdev_region(my_dev_no,1);
            return err;
        }

        dev = device_create(my_class, NULL, my_dev_no, NULL, MY_DEV_NAME);
        if (IS_ERR(dev)) {
            err = PTR_ERR(dev);
            class_destroy(my_class);
            cdev_del(&my_cdev);
            unregister_chrdev_region(my_dev_no,1);
            return err;
        }

        pr_info("my_dev module init ok\n");
        my_buf_len = 0;
        memset(my_kbuf, 0, MY_BUF_SIZE);
        return 0;
    }

    static void __exit my_dev_exit(void)
    {
        device_destroy(my_class, my_dev_no);
        class_destroy(my_class);
        cdev_del(&my_cdev);
        unregister_chrdev_region(my_dev_no, 1);
        pr_info("my_dev module exit ok\n");
    }

    module_init(my_dev_init);
    module_exit(my_dev_exit);

    MODULE_LICENSE("GPL");
    MODULE_DESCRIPTION("Simple char dev homework compare with kfd_chardev.c");
    MODULE_AUTHOR("homework");


Makefile
--------------------------

.. code-block:: Makefile

    obj-m := my_dev.o
    KDIR := /lib/modules/$(shell uname -r)/build
    PWD := $(shell pwd)

    all:
        $(MAKE) -C $(KDIR) M=$(PWD) modules

    clean:
        $(MAKE) -C $(KDIR) M=$(PWD) clean


测试脚本
--------------------------

.. code-block:: shell

    make
    sudo insmod my_dev.ko
    ls /dev/my_dev
    dmesg -w

    # 测试写
    echo "hello rocm kfd" > /dev/my_dev

    # 测试读
    cat /dev/my_dev

    sudo rmmod my_dev

输出结果
--------------------------

.. code-block:: text

    my_dev: open() called pid=xxx
    my_dev: write() count=xxx offset=0
    my_dev: release() called pid=xxx

    my_dev: open() called pid=xxx
    my_dev: read() count=xxx offset=0
    my_dev: release() called pid=xxx

关键知识点 + 坑点讲解
--------------------------

1. 字符设备注册流程
+++++++++++++++++++++++++++++

    1. `alloc_chrdev_region(&devno, baseminor, count, name)`：动态申请主设备号；替代旧版 `register_chrdev`。
    2. `cdev_init(struct cdev *, &fops)`：初始化 cdev 结构体，绑定 file_operations。
    3. `cdev_add()`：把 cdev 注册进内核， **从此设备可以被 open** 。
    4. 卸载逆序： `cdev_del()` ， `unregister_chrdev_region()` 。

2. read /write，__user 指针大坑
++++++++++++++++++++++++++++++++++++++

    1. 内核空间和用户空间是隔离的，不能直接访问用户空间的指针。
    2. 必须使用 `copy_to_user()` 和 `copy_from_user()` 来进行数据传输。
    3. 返回值必须是实际读写的字节数，不能返回0（除非EOF）。


3. 用户态行为现象
++++++++++++++++++++++++++++++++++++++

    1. `echo "xxx" > /dev/my_dev`：open，write，close (release)。会覆盖内核缓冲区。
    2. `cat /dev/my_dev`：open，循环 read；read 返回 0 (EOL)，cat 退出，release。

4. 真实驱动不要全局缓冲区
++++++++++++++++++++++++++++++++++++++

    1. 真实驱动每个进程应该有自己的内核对象，挂到 `file->private_data`。
    2. KFD 驱动就是每个 open 分配一个 `kfd_process`，close 时释放。
