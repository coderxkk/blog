.. meta::
   :description: linux内核和模块的编译方法
   :keywords: linux, module, 编译

########################
Linux内核与模块的编译
########################

内核模块编译
================

linux开发包环境

.. code-block:: shell

    sudo apt update
    sudo apt install linux-headers-$(uname -r)
    sudo apt install build-essential linux-headers-$(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build

Makefile

.. code-block:: shell

    obj-m += hello.o
    all:
        make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
    clean:
        make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

最简单的内核模块示例

.. code-block:: c
    
    // hello.c
    #include <linux/init.h>
    #include <linux/module.h>
    MODULE_LICENSE("GPL");
    static int __init hello_init(void) {
        pr_info("hello kfd: init\n");
        return 0;
    }
    static void __exit hello_exit(void) {
        pr_info("hello kfd: exit\n");
    }
    module_init(hello_init);
    module_exit(hello_exit);

运行流程

.. code-block:: shell

    # 1. 编译模块
    make

    # 2. 查看模块信息（加载前）
    modinfo hello.ko

    # 3. 加载模块
    sudo insmod hello.ko
    # 输出到内核日志：hello kfd: init

    # 4. 查看内核日志
    dmesg | tail -5
    # [12345.678] hello kfd: init

    # 5. 列出已加载模块
    lsmod | grep hello

    # 6. 卸载模块
    sudo rmmod hello
    # 输出到内核日志：hello kfd: exit

    # 7. 再次查看日志
    dmesg | tail -5
    # [12345.890] hello kfd: exit

多源文件情况

.. code-block:: shell
    
    # mymodule 是模块名称
    obj-m += mymodule.o

    # 指定源文件
    mymodule-objs := main.o helper.o utils.o

模块生命周期示意图

.. code-block:: shell

    用户态                   内核态
    |                        |
    |  insmod hello.ko      |
    |----------------------->|
    |                        |  module_init(hello_init)
    |                        |      ↓
    |                        |  hello_init() 执行
    |                        |      ↓
    |                        |  返回 0 (成功)
    |  <---------------------|
    |  模块已加载            |
    |                        |
    |  使用模块功能...       |
    |                        |
    |  rmmod hello          |
    |----------------------->|
    |                        |  module_exit(hello_exit)
    |                        |      ↓
    |                        |  hello_exit() 执行
    |                        |      ↓
    |                        |  释放资源
    |  <---------------------|
    |  模块已卸载            |


带参数的简单用例

.. code-block:: c

    // hello.c
    #include <linux/init.h>
    #include <linux/module.h>
    #include <linux/kernel.h>

    MODULE_LICENSE("GPL");
    MODULE_AUTHOR("kunkun");
    MODULE_DESCRIPTION("module_param demo");

    /* ① int 参数：变量必须是全局(静态)变量，初始值就是"不传参时的默认值" */
    static int count = 1;
    module_param(count, int, 0644);
    MODULE_PARM_DESC(count, "print times, default 1");

    /* ② 字符串参数：内核里字符串类型叫 charp(char pointer)，不是 string！ */
    static char *who = "kfd";
    module_param(who, charp, 0644);
    MODULE_PARM_DESC(who, "name to greet, default kfd");

    static int __init hello_init(void)
    {
        int i;

        /* 进入 init 时，insmod 传入的值已经被内核解析并写进变量了 */
        pr_info("hello: load with count=%d who=%s\n", count, who);

        for (i = 0; i < count; i++)
            pr_info("hello: [%d/%d] greet %s\n", i + 1, count, who);

        return 0;   /* 返回 0 = 加载成功；返回负数 errno 会让 insmod 失败 */
    }

    static void __exit hello_exit(void)
    {
        pr_info("hello: unload, last count=%d\n", count);
    }

    module_init(hello_init);
    module_exit(hello_exit);

带参数的用例运行

.. code-block:: shell

    sudo insmod hello.ko count=5 who=KFD

主线内核编译
==============================

1. 安装编译依赖

.. code-block:: shell

    sudo apt update
    sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev bc kmod cpio dwarves zstd xz-utils rsync git

2. 获取源码，浅克隆指定 tag，省时间省空间

.. code-block:: shell

    mkdir -p ~/kfd-study && cd ~/kfd-study
    git clone --depth 1 --branch v6.8 https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
    cd linux

3. 生成 .config

.. code-block:: shell

    # ① 编译内核镜像 + 全部模块
    make -j$(nproc)

    # ② 安装模块到 /lib/modules/6.8.0-kfdstudy/
    sudo make modules_install -j$(nproc)

    # ③ 安装内核：自动拷贝 bzImage/System.map 到 /boot、生成 initramfs、更新 GRUB
    sudo make install