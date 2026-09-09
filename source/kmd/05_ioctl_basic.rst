.. meta::
   :description: ioctl系统调用基础知识
   :keywords: linux, module, 编译

########################
ioctl系统调用基础
########################

核心概念
==================================

unlocked_ioctl
--------------------------

`unlocked_ioctl`：现代内核标准 ioctl 回调，不再持有大内核锁 BKL。

.. code-block:: c

    struct file_operations {
        ...
        long (*unlocked_ioctl) (struct file * file, unsigned int cmd, unsigned long arg);
        ...
    };


compat_ioctl
--------------------------

`compat_ioctl` 的引入，主要解决的是架构兼容性问题，与锁的演进关系不大。当一个 32 位的应用程序在 64 位内核上运行时，它传递的 ioctl 命令码（cmd）和参数（arg）的数据结构可能存在差异（例如，long 类型在 32 位下是 4 字节，在 64 位下是 8 字节）。

`compat_ioctl` 的作用就是作为一个翻译层，它需要：

    1. 接收来自 32 位进程的原始参数。
    2. 将这些参数从 32 位的数据结构“翻译”或“转换”为 64 位内核能够理解的本地数据结构。
    3. 在完成转换后，通常会调用核心的 unlocked_ioctl 处理逻辑。

.. code-block:: c

    struct file_operations {
        ...
        long (*compat_ioctl) (struct file * file, unsigned int cmd, unsigned long arg);
        ...
    };

ioctl命令码编码规则
--------------------------

`_IO / _IOR / _IOW / _IOWR` 宏

.. code-block:: c

    // 无参数
    #define MY_IOCTL_MAGIC 'k'
    #define IOCTL_CMD0 _IO(MY_IOCTL_MAGIC, 0)
    // IOR：内核读数据，返回给用户
    #define IOCTL_CMD_GET _IOR(MY_IOCTL_MAGIC,1,int)
    // IOW：用户写数据给到内核
    #define IOCTL_CMD_SET _IOW(MY_IOCTL_MAGIC,2,int)
    // IOWR：双向读写
    #define IOCTL_CMD_TW _IOWR(MY_IOCTL_MAGIC,3,struct my_param)

ioctl调用栈
--------------------------

打开 `fs/ioctl.c`，简单浏览系统调用入口 `sys_ioctl` 链路：

**用户态 ioctl () → sys_ioctl → vfs_ioctl → 调用驱动 unlocked_ioctl**

copy_from_user / copy_to_user
----------------------------------------

内核空间地址和用户空间地址是隔离的，不能直接访问用户空间的指针。必须使用 `copy_to_user()` 和 `copy_from_user()` 来进行数据传输。

内核空间和用户空间的页表不同。内核空间是全局共享的内核页表，用户空间是普通用户进程页表。并且，内核空间和用户空间的访问权限不同，可能会导致内核访问用户空间时触发页错误（page fault）或访问违规。因此，直接使用用户空间的指针在内核中是危险的。

如下是一个简单的 ioctl 回调示例，展示了如何使用 `copy_to_user` 和 `copy_from_user`：

.. code-block:: c

    long my_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
    {
        int ret = 0;
        int val;

        switch (cmd) {
        case IOCTL_CMD_GET:
            val = 123; // 内核数据
            if (copy_to_user((int __user *)arg, &val, sizeof(val)))
                ret = -EFAULT;
            break;
        case IOCTL_CMD_SET:
            if (copy_from_user(&val, (int __user *)arg, sizeof(val)))
                ret = -EFAULT;
            pr_info("my_ioctl: set val=%d\n", val);
            break;
        default:
            ret = -EINVAL;
            break;
        }
        return ret;
    }

ioctl简单demo
==================================

沿用 04_char_dev_driver.rst 的字符设备驱动，增加 ioctl 功能。

my_dev.c 字符设备驱动文件添加如下关于ioctl的代码：

.. code-block:: c

    #include "my_ioctl.h"

    // 内核内部缓冲区
    static uint32_t kernel_buf = 0;

    // unlocked_ioctl 回调
    static long my_unlocked_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
    {
        struct my_ioctl_arg arg_data;

        switch (cmd) {
        case MY_CMD_CALC:
            // arg是用户态指针，copy_from_user读取结构体
            if (copy_from_user(&arg_data, (void __user *)arg, sizeof(arg_data))) {
                pr_err("MY_CMD_CALC copy_from_user failed\n");
                return -EFAULT;
            }
            arg_data.out_val = arg_data.in_val * 2;
            // 写回用户空间
            if (copy_to_user((void __user *)arg, &arg_data, sizeof(arg_data))) {
                pr_err("MY_CMD_CALC copy_to_user failed\n");
                return -EFAULT;
            }
            pr_info("MY_CMD_CALC: in=%u, out=%u\n", arg_data.in_val, arg_data.out_val);
            break;

        case MY_CMD_CLEAR:
            kernel_buf = 0;
            pr_info("MY_CMD_CLEAR: kernel buffer cleared\n");
            break;

        default:
            pr_err("unknown ioctl cmd: %u\n", cmd);
            return -ENOTTY;
        }
        return 0;
    }

    // 兼容32位用户程序，这里简单返回0
    static long my_compat_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
    {
        return my_unlocked_ioctl(file, cmd, arg);
    }

    /* 文件操作表，对标 KFD kfd_fops */
    static const struct file_operations my_dev_fops = {
        .owner   = THIS_MODULE,
        .open    = my_dev_open,
        .release = my_dev_release,
        .read    = my_dev_read,
        .write   = my_dev_write,
        .unlocked_ioctl = my_unlocked_ioctl,
        .compat_ioctl = my_compat_ioctl,
    };

arg结构体定义，定义再 my_ioctl.h 头文件中：

.. code-block:: c

    #ifndef MY_IOCTL_H
    #define MY_IOCTL_H

    #ifdef __KERNEL__
    // 内核侧编译：用内核类型头文件
    #include <linux/types.h>
    #else
    // 用户态编译：才用 stdint.h
    #include <stdint.h>
    #endif

    // 内核里会自动替换为内核头文件，用户态直接使用
    struct my_ioctl_arg {
        uint32_t in_val;
        uint32_t out_val;
    };

    // 定义ioctl命令，推荐 _IOWR：双向读写
    #define MY_IOC_MAGIC  'm'
    #define MY_CMD_CALC    _IOWR(MY_IOC_MAGIC, 1, struct my_ioctl_arg) // 命令1：in_val*2 → out_val
    #define MY_CMD_CLEAR   _IO(MY_IOC_MAGIC, 2)                        // 命令2：清空内核缓冲区

    #endif


编译、加载、测试

.. code-block:: shell

    # 1. 编译内核模块
    make

    # 2. 加载内核模块
    sudo insmod my_dev.ko

    # 3. 确认设备节点生成
    ls /dev/my_dev
    # 查看主设备号
    cat /proc/devices | grep my_dev

    # 4. 编译用户态程序
    gcc user_test.c -o user_test

    # 5. 运行测试程序
    sudo ./user_test

    # 新开终端实时看内核打印
    dmesg -w

    # 6. 卸载模块
    sudo rmmod my_dev
    make clean
