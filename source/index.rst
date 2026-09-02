.. title:: koi-blogs | GPU 系统技术笔记
.. meta::
   :description: zekun.wang 的 GPU 系统技术博客，记录 AMDGPU、ROCm、Linux 内核与 CUDA 技术解析。

:html_theme.sidebar_secondary.remove:

.. raw:: html

   <div class="home-shell">
     <section class="home-hero" aria-labelledby="home-title">
       <div class="hero-copy">
         <p class="hero-kicker"><span></span> GPU SYSTEMS NOTES</p>
         <h1 id="home-title">从驱动到计算栈，<br><em>拆开每一层。</em></h1>
         <p class="hero-lead">记录 AMDGPU、ROCm、Linux 内核与 CUDA 的源码阅读和工程实践，理解 GPU 软件栈真正如何工作。</p>
         <div class="hero-actions">
           <a class="home-button home-button--primary" href="#columns">浏览技术专栏</a>
           <a class="home-button home-button--ghost" href="https://github.com/coderxkk" target="_blank" rel="noopener noreferrer">访问 GitHub <span aria-hidden="true">↗</span></a>
         </div>
       </div>
       <aside class="profile-card" aria-label="个人介绍">
         <div class="profile-topline"><span>ABOUT</span><span>01 / 04</span></div>
         <img class="profile-avatar" src="https://github.com/coderxkk.png?size=320" alt="zekun.wang 的头像" width="160" height="160">
         <div class="profile-copy">
           <p class="profile-name">zekun.wang</p>
           <p class="profile-role">GPU 系统技术探索者</p>
           <p class="profile-bio">关注 Linux 图形驱动、ROCm 运行时与异构计算。这里既有源码脉络，也有可以复现的实践记录。</p>
         </div>
         <div class="profile-tags" aria-label="关注领域">
           <span>Linux Kernel</span><span>ROCm</span><span>GPU Driver</span>
         </div>
       </aside>
     </section>

     <section class="columns-section" id="columns" aria-labelledby="columns-title">
       <div class="section-heading">
         <div>
           <p class="section-eyebrow">KNOWLEDGE COLUMNS</p>
           <h2 id="columns-title">四条路径，理解完整 GPU 栈</h2>
         </div>
         <p>从内核态到用户态，从硬件架构到计算平台。选择一个入口，开始向下探索。</p>
       </div>

       <div class="column-grid">
         <a class="column-card column-card--kmd" href="kmd/index.html">
           <span class="column-index">01</span>
           <div class="column-mark">KMD</div>
           <div class="column-content">
             <p class="column-label">KERNEL MODE DRIVER</p>
             <h3>KMD 专栏</h3>
             <p>走进 Linux 内核、AMDGPU 与 KFD，梳理驱动初始化、内存管理和调试链路。</p>
           </div>
           <span class="column-link">进入专栏 <span aria-hidden="true">→</span></span>
         </a>

         <a class="column-card column-card--umd" href="umd/index.html">
           <span class="column-index">02</span>
           <div class="column-mark">UMD</div>
           <div class="column-content">
             <p class="column-label">USER MODE DRIVER</p>
             <h3>UMD 专栏</h3>
             <p>追踪用户态运行时与内核驱动的连接方式，理解 ROCr、Thunk 和设备交互。</p>
           </div>
           <span class="column-link">进入专栏 <span aria-hidden="true">→</span></span>
         </a>

         <a class="column-card column-card--amd" href="amd/index.html">
           <span class="column-index">03</span>
           <div class="column-mark">AMD</div>
           <div class="column-content">
             <p class="column-label">ARCHITECTURE &amp; ECOSYSTEM</p>
             <h3>AMD 技术解析</h3>
             <p>解析 AMD GPU 架构、ROCm 软件生态与核心组件，建立系统化技术视图。</p>
           </div>
           <span class="column-link">进入专栏 <span aria-hidden="true">→</span></span>
         </a>

         <a class="column-card column-card--cuda" href="cuda/index.html">
           <span class="column-index">04</span>
           <div class="column-mark">CUDA</div>
           <div class="column-content">
             <p class="column-label">PARALLEL COMPUTING</p>
             <h3>CUDA 技术解析</h3>
             <p>从编程模型到性能优化，拆解线程组织、内存层次与 GPU 并行计算方法。</p>
           </div>
           <span class="column-link">进入专栏 <span aria-hidden="true">→</span></span>
         </a>
       </div>
     </section>

     <section class="home-manifesto" aria-label="博客理念">
       <p>READ · TRACE · EXPLAIN</p>
       <blockquote>不止记录“怎么做”，也追问“为什么这样工作”。</blockquote>
     </section>
   </div>

.. toctree::
   :hidden:
   :maxdepth: 2

   kmd/index
   umd/index
   amd/index
   cuda/index
