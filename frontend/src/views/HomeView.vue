<template>
  <div class="home">

    <!-- ============================================================
         Hero 区 · 品牌主张
         ============================================================ -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-kicker">
          <span class="kicker-dot"></span>
          AI 创造力大赛 · 一句话烧出专属陶艺
        </div>
        <h1 class="hero-title">
          一句话，
          <span class="highlight">烧</span>出一件
          <br class="only-lg" />
          只属于你的陶瓷
        </h1>
        <p class="hero-lead">
          陶语把"自然语言到陶瓷造型"的翻译交给大模型，把烧窑的事还给手艺人。
          <br />
          从想法到收到实物，平均 7 - 10 天。
        </p>
        <div class="hero-cta">
          <router-link to="/design" class="btn btn-primary">
            <span>现在试试</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M13 5l7 7-7 7"></path>
            </svg>
          </router-link>
          <a href="#problem" class="btn btn-ghost">了解痛点</a>
        </div>

        <div class="hero-stats">
          <div class="stat">
            <div class="stat-num">5</div>
            <div class="stat-label">产区合作</div>
          </div>
          <div class="stat-sep"></div>
          <div class="stat">
            <div class="stat-num">30s</div>
            <div class="stat-label">方案生成</div>
          </div>
          <div class="stat-sep"></div>
          <div class="stat">
            <div class="stat-num">7-10</div>
            <div class="stat-label">烧制天</div>
          </div>
          <div class="stat-sep"></div>
          <div class="stat">
            <div class="stat-num">6色</div>
            <div class="stat-label">可选釉色</div>
          </div>
        </div>
      </div>

      <!-- 右侧陶瓷插画 -->
      <div class="hero-visual">
        <div class="visual-ring"></div>
        <div class="visual-chip chip-1">玉兔捧月</div>
        <div class="visual-chip chip-2">月形花瓶</div>
        <div class="visual-chip chip-3">三孔香插</div>
        <div class="visual-chip chip-4">怀宠橘猫</div>
        <img
          src="@/assets/hero-ceramic.png"
          alt="陶语定制陶瓷 - 兔月香薰瓶"
          class="hero-ceramic-img"
        />
      </div>
    </section>

    <!-- ============================================================
         问题 · 痛点拆解
         ============================================================ -->
    <section id="problem" class="section">
      <div class="section-header">
        <span class="section-kicker">问题</span>
        <h2 class="section-title">想要一件"懂自己"的陶瓷，为什么这么难</h2>
        <p class="section-sub">标品千篇一律，定制门槛又太高。我们调研了需求侧与供给侧，两端都在喊累。</p>
      </div>

      <div class="problem-grid">
        <div class="problem-card" v-for="(p, i) in problems" :key="i">
          <div class="problem-num">{{ String(i + 1).padStart(2, '0') }}</div>
          <h3 class="problem-title">{{ p.title }}</h3>
          <p class="problem-desc">{{ p.desc }}</p>
          <div class="problem-tag">{{ p.tag }}</div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         产品体验演示 · 对话式设计台
         ============================================================ -->
    <section id="demo" class="section section-warm">
      <div class="section-header">
        <span class="section-kicker">产品体验</span>
        <h2 class="section-title">对话式设计台 · 你描述，AI 拉坯</h2>
        <p class="section-sub">输入一句自然语言，30 秒生成 3 个可旋转 3D 方案；满意就一键下单，工作室同步收到工单。</p>
      </div>

      <div class="demo-panel">
        <!-- 左侧：对话流 -->
        <div class="demo-chat">
          <div class="chat-message msg-user">
            想送妈妈一个生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关。
          </div>
          <div class="chat-message msg-bot">
            <strong>陶语 · </strong>收到。关键词解析：<br />
            🐰 兔子造型 / 🌙 月亮意象 / 🌼 桂花纹样 / <br />
            冷白釉 / 玄关尺寸（建议 18 - 22cm）<br />
            正在为你拉坯…
          </div>
          <div class="chat-message msg-bot">
            <strong>陶语 · </strong>三个方案出炉啦：<br />
            ① <b>玉兔捧月</b>（坐姿，月亮中空可放干花）<br />
            ② <b>月下折桂</b>（兔耳化作桂枝）<br />
            ③ <b>望舒</b>（极简款，月牙底座）<br />
            👉 点击右侧方案可旋转查看，选中后可以微调细节。
          </div>
          <div class="chat-message msg-user">第①个，把兔子耳朵再长一点点。</div>
          <div class="chat-message msg-bot">
            <strong>陶语 · </strong>已调整 ✅ 报价 ¥386，景德镇 · 陶溪川 · 林师傅承接，预计 9 天到手。是否下单？
          </div>

          <div class="chat-input-bar">
            <div class="chat-placeholder">再来一句试试…</div>
            <button class="chat-send-btn" @click="goDesign">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 右侧：产品预览 -->
        <div class="demo-preview">
          <div class="preview-float">
            <img
              src="@/assets/玉兔捧月.png"
              alt="玉兔捧月 - 陶瓷摆件"
              class="preview-img"
            />
          </div>
          <div class="preview-caption">
            <div class="caption-title text-display">玉兔捧月</div>
            <div class="caption-meta">¥386 · 冷白釉 · 18cm · 景德镇</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         五步技术链路
         ============================================================ -->
    <section class="section">
      <div class="section-header">
        <span class="section-kicker">技术链路</span>
        <h2 class="section-title">从一句话到一件瓷器，只有五步</h2>
        <p class="section-sub">语义理解 → 方案生成 → 对话微调 → 智能派单 → 烧制配送，每一步都经过工艺校验。</p>
      </div>

      <div class="flow-grid">
        <div class="flow-step" v-for="(step, i) in flow" :key="i" :style="{ animationDelay: `${i * 0.08}s` }">
          <div class="flow-icon">
            <span class="icon-text">{{ step.icon }}</span>
          </div>
          <h4 class="flow-title">{{ step.title }}</h4>
          <p class="flow-desc">{{ step.desc }}</p>
          <div v-if="i < flow.length - 1" class="flow-arrow">→</div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         四个真实场景
         ============================================================ -->
    <section class="section section-warm">
      <div class="section-header">
        <span class="section-kicker">使用场景</span>
        <h2 class="section-title">四种人，四种烧进釉里的故事</h2>
        <p class="section-sub">不只是摆件，是把心意、记忆、审美、故事，一起烧进釉里。</p>
      </div>

      <div class="scene-grid">
        <div class="scene-card" v-for="(s, i) in scenes" :key="i">
          <div class="scene-header">
            <div class="scene-num">0{{ i + 1 }}</div>
            <div class="scene-title-bar">
              <h3 class="scene-title text-display">{{ s.title }}</h3>
              <div class="scene-for">{{ s.for }}</div>
            </div>
          </div>
          <p class="scene-desc">{{ s.desc }}</p>
          <blockquote class="scene-quote">
            <span class="quote-mark">"</span>
            {{ s.quote }}
            <span class="quote-mark end">"</span>
          </blockquote>
          <div class="scene-byline">—— {{ s.by }}</div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         三角价值
         ============================================================ -->
    <section class="section">
      <div class="section-header">
        <span class="section-kicker">价值</span>
        <h2 class="section-title">三个维度，一起让陶瓷更轻盈</h2>
      </div>

      <div class="value-grid">
        <div class="value-card" v-for="(v, i) in values" :key="i">
          <div class="value-num">{{ v.num }}</div>
          <h3 class="value-title">{{ v.title }}</h3>
          <p class="value-desc">{{ v.desc }}</p>
        </div>
      </div>
    </section>

    <!-- ============================================================
         非遗工作室合作
         ============================================================ -->
    <section class="section">
      <div class="heritage-panel">
        <div class="heritage-left">
          <div class="heritage-kicker">
            <span class="kicker-dot"></span>
            非遗工作室合作 · 社会公益
          </div>
          <h3 class="heritage-title">
            让手艺扎实的工作室<br />
            接到真正属于自己的订单
          </h3>
          <p class="heritage-desc">
            景德镇、德化、宜兴、建水有大量手艺扎实但不擅长线上运营的工作室。陶语目标深度合作 20 家伙伴，平台不抽设计费，仅对成单部分收取 8% 平台费。
          </p>

          <div class="heritage-pills">
            <span v-for="(p, i) in heritagePills" :key="i" class="pill">{{ p }}</span>
          </div>

          <div class="heritage-cta">
            <router-link to="/design" class="btn btn-primary-light">
              <span>设计我的陶瓷</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M13 5l7 7-7 7"></path>
              </svg>
            </router-link>
          </div>
        </div>

        <div class="heritage-right">
          <div class="heritage-stat">
            <div class="h-num">20</div>
            <div class="h-label">家目标深度合作工作室</div>
          </div>
          <div class="heritage-stat">
            <div class="h-num">5</div>
            <div class="h-label">位目标非遗传承人席位</div>
          </div>
          <div class="heritage-stat">
            <div class="h-num">8<span class="percent">%</span></div>
            <div class="h-label">目标平台费率</div>
          </div>
          <div class="heritage-stat">
            <div class="h-num">0</div>
            <div class="h-label">元设计师费用，AI 替代</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         Footer
         ============================================================ -->
    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="footer-seal">陶</span>
          <div>
            <div class="footer-name text-display">陶语 · ClayWords</div>
            <div class="footer-slogan">AI 创造力大赛 · 一句话烧出专属陶瓷</div>
          </div>
        </div>
        <div class="footer-meta">
          © 2026 ClayWords · 让非遗手艺触手可及
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()

const problems = [
  {
    tag: '需求侧 · 01',
    title: '找不到，也撞款',
    desc: '电商平台陶瓷摆件高度同质化，想要"像我家橘猫坐在月亮上"这种叙事性造型，几乎搜不到。'
  },
  {
    tag: '需求侧 · 02',
    title: '沟通成本高得离谱',
    desc: '找工作室定制平均要 5 - 8 轮文字加草图来回，效果还要等打样才能看到，定金一付就是沉没成本。'
  },
  {
    tag: '供给侧 · 03',
    title: '师傅 60% 时间在聊天',
    desc: '中小工作室和非遗手艺人接单靠熟人和私域，沟通占掉大半精力，真正拉坯烧窑的时间被严重挤压。'
  }
]

const flow = [
  { icon: '壹', title: '语义理解', desc: '大模型解析造型、釉色、尺寸、用途与情感意象' },
  { icon: '贰', title: '方案生成', desc: '结合陶瓷工艺约束，生成三个可烧制的 3D 方案' },
  { icon: '叁', title: '对话微调', desc: '所见即所得，一句话调整细节（耳朵再长一点）' },
  { icon: '肆', title: '智能派单', desc: '按工艺、产能、地域匹配最合适的手艺人' },
  { icon: '伍', title: '烧制配送', desc: '师傅烧窑 · 平台质检 · 顺丰直送' }
]

const scenes = [
  {
    title: '礼 · 寄情',
    for: '送给重要的人',
    desc: '把回忆、故事和心意一同烧进釉里。',
    quote: '我想要一个像我们第一次约会那家咖啡馆窗台上那盆绿萝的花瓶。',
    by: '小雨，27 岁'
  },
  {
    title: '念 · 怀宠',
    for: '留下毛孩子的样子',
    desc: '比相框更有温度的纪念，让它一直陪在身边。',
    quote: '我家糖糕走了，能做一个它最爱的趴在窗台晒太阳的样子吗？',
    by: '王女士，34 岁'
  },
  {
    title: '居 · 安宅',
    for: '给自己的家定调',
    desc: '新中式、侘寂、治愈系，一件主角摆件定调整个空间。',
    quote: '玄关想要一件有"山"的感觉的，不要太具象，颜色要哑光。',
    by: '阿哲，31 岁'
  },
  {
    title: '赠 · 联名',
    for: '品牌 / 博主做限定',
    desc: '独立品牌、内容创作者做小批量限定周边，30 - 100 件起订。',
    quote: '想给读者做 50 个生日礼物，预算每个 200 内，要带签名编号。',
    by: '小宇，博主'
  }
]

const values = [
  { num: '效率', title: '从 2 - 3 周 → 7 - 10 天', desc: '5 - 8 轮沟通压缩成 1 - 2 轮确认，AI 替你把图纸画好。' },
  { num: '商业', title: '填补 200 - 800 元市场空白', desc: '从"高门槛非标服务"变成"所见即所得的轻量消费"，平台抽佣 + 材质升级形成稳定营收。' },
  { num: '社会', title: '给手艺人装一条数字化管道', desc: '平台预付 30%，AI 翻译需求替师傅省掉 60% 沟通时间，让手艺回到拉坯烧窑本身。' }
]

const heritagePills = [
  '流量与订单调度',
  'AI 翻译需求 · 省掉 60% 沟通',
  '平台预付 30%',
  '师傅签名款 IP 沉淀',
  '景德镇 · 陶溪川',
  '德化 · 白瓷',
  '宜兴 · 紫砂',
  '建水 · 紫陶',
  '非遗传承人专属通道'
]

function goDesign() {
  router.push('/design')
}
</script>

<style scoped>
/* ============================================================
   通用区块
   ============================================================ */
.home {
  color: var(--color-text-primary);
  background: var(--color-background);
}

.section {
  padding: var(--spacing-20) var(--spacing-8);
  max-width: var(--container-xl);
  margin: 0 auto;
  position: relative;
}

.section-warm {
  background: linear-gradient(180deg, transparent 0%, rgba(212, 165, 116, 0.06) 30%, rgba(201, 123, 90, 0.05) 70%, transparent 100%);
}

.section-header {
  text-align: center;
  margin-bottom: var(--spacing-12);
  max-width: 760px;
  margin-left: auto;
  margin-right: auto;
}

.section-kicker {
  display: inline-block;
  font-size: var(--font-size-sm);
  color: var(--color-accent);
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: var(--spacing-4);
  font-family: var(--font-family-mono);
  font-weight: 500;
}

.section-title {
  font-family: var(--font-family-display);
  font-size: clamp(28px, 3.5vw, 42px);
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.4;
  letter-spacing: 2px;
  margin-bottom: var(--spacing-4);
}

.section-sub {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.9;
}

/* ============================================================
   Hero 区
   ============================================================ */
.hero {
  position: relative;
  min-height: 620px;
  padding: var(--spacing-20) var(--spacing-8) var(--spacing-16);
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: var(--spacing-12);
  align-items: center;
  max-width: var(--container-xl);
  margin: 0 auto;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 15% 20%, rgba(201, 123, 90, 0.08), transparent 50%),
    radial-gradient(ellipse at 85% 80%, rgba(123, 155, 168, 0.08), transparent 50%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 2;
  animation: fadeInUp 0.8s var(--easing-standard) both;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 6px 16px;
  background: rgba(201, 123, 90, 0.08);
  border: 1px solid rgba(201, 123, 90, 0.18);
  border-radius: 999px;
  font-size: var(--font-size-sm);
  color: var(--color-accent-dark);
  font-family: var(--font-family-mono);
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-6);
}

.kicker-dot {
  width: 6px;
  height: 6px;
  background: var(--color-accent);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.hero-title {
  font-family: var(--font-family-display);
  font-size: clamp(40px, 5.5vw, 64px);
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.2;
  letter-spacing: 3px;
  margin-bottom: var(--spacing-6);
}

.hero-title .highlight {
  color: var(--color-accent);
  position: relative;
  display: inline-block;
}
.hero-title .highlight::after {
  content: '';
  position: absolute;
  left: -4px;
  right: -4px;
  bottom: 6px;
  height: 16px;
  background: rgba(201, 123, 90, 0.18);
  z-index: -1;
  border-radius: 4px;
}

.hero-lead {
  font-size: var(--font-size-lg);
  line-height: 2;
  color: var(--color-text-secondary);
  max-width: 620px;
  margin-bottom: var(--spacing-8);
}

.hero-cta {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-12);
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 14px 28px;
  font-size: var(--font-size-base);
  font-weight: 500;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: all var(--transition-normal);
  text-decoration: none;
  letter-spacing: 1px;
}
.btn svg {
  width: 18px;
  height: 18px;
  transition: transform var(--transition-fast);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 6px 20px rgba(45, 74, 72, 0.25);
}
.btn-primary:hover {
  background: var(--color-primary-dark);
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(45, 74, 72, 0.32);
}
.btn-primary:hover svg {
  transform: translateX(4px);
}

.btn-primary-light {
  background: rgba(255, 253, 249, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
}
.btn-primary-light:hover {
  background: rgba(255, 255, 255, 0.18);
  transform: translateY(-2px);
}
.btn-primary-light svg { color: #fff; }

.btn-ghost {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-border);
}
.btn-ghost:hover {
  background: rgba(45, 74, 72, 0.04);
  border-color: var(--color-primary-light);
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-6);
  padding: var(--spacing-5) var(--spacing-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  max-width: 560px;
  box-shadow: var(--shadow-sm);
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-num {
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1;
  letter-spacing: 1px;
}
.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}
.stat-sep {
  width: 1px;
  height: 36px;
  background: var(--color-border-light);
}

/* ======= Hero 右侧视觉 ======= */
.hero-visual {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  animation: fadeIn 1s 0.3s var(--easing-standard) both;
}

.visual-ring {
  position: absolute;
  width: 460px;
  height: 460px;
  border: 1px solid var(--color-border-light);
  border-radius: 50%;
}
.visual-ring::before,
.visual-ring::after {
  content: '';
  position: absolute;
  border: 1px dashed rgba(201, 123, 90, 0.2);
  border-radius: 50%;
}
.visual-ring::before { inset: 40px; }
.visual-ring::after { inset: 80px; border-color: rgba(45, 74, 72, 0.1); }

.hero-ceramic-img {
  width: 380px;
  max-width: 100%;
  height: auto;
  position: relative;
  z-index: 2;
  animation: float 5s ease-in-out infinite;
  object-fit: contain;
}

.visual-chip {
  position: absolute;
  padding: 8px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-full);
  font-family: var(--font-family-display);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
  z-index: 3;
  animation: float 6s ease-in-out infinite;
}
.chip-1 { top: 8%; left: 0%; animation-delay: 0s; }
.chip-2 { top: 20%; right: -4%; animation-delay: 1s; }
.chip-3 { bottom: 18%; left: -4%; animation-delay: 2s; }
.chip-4 { bottom: 8%; right: 2%; animation-delay: 1.5s; }

/* ============================================================
   问题卡片
   ============================================================ */
.problem-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-6);
}

.problem-card {
  position: relative;
  padding: var(--spacing-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  transition: all var(--transition-normal);
}
.problem-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-accent-light);
  box-shadow: var(--shadow-lg);
}

.problem-num {
  position: absolute;
  top: var(--spacing-5);
  right: var(--spacing-6);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 2px;
}

.problem-tag {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(201, 123, 90, 0.1);
  color: var(--color-accent-dark);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  margin-bottom: var(--spacing-3);
}

.problem-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-3);
  letter-spacing: 1px;
}

.problem-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.9;
}

/* ============================================================
   产品体验演示
   ============================================================ */
.demo-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-8);
  padding: var(--spacing-10);
  background: linear-gradient(135deg, var(--color-surface) 0%, #f5efe2 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-lg);
  align-items: center;
}

.demo-chat {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.chat-message {
  padding: 14px 18px;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-base);
  line-height: 1.9;
  animation: fadeInUp 0.6s var(--easing-standard) both;
}

.msg-user {
  background: var(--color-primary);
  color: #fff;
  margin-left: 20%;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(45, 74, 72, 0.2);
}
.msg-user strong { color: #fff9e8; }

.msg-bot {
  background: var(--color-surface);
  color: var(--color-text-primary);
  margin-right: 10%;
  border: 1px solid var(--color-border-light);
  border-bottom-left-radius: 4px;
}
.msg-bot strong {
  color: var(--color-accent-dark);
  font-weight: 600;
  font-family: var(--font-family-display);
  letter-spacing: 1px;
}
.msg-bot b { color: var(--color-accent-dark); }

.chat-input-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-4) var(--spacing-5);
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-xl);
  margin-top: var(--spacing-3);
}

.chat-placeholder {
  flex: 1;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-base);
}

.chat-send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: 0 4px 12px rgba(201, 123, 90, 0.3);
}
.chat-send-btn:hover {
  background: var(--color-accent-dark);
  transform: rotate(-15deg);
}
.chat-send-btn svg { width: 20px; height: 20px; }

/* ======= 产品预览 ======= */
.demo-preview {
  text-align: center;
}

.preview-float {
  display: inline-block;
  padding: var(--spacing-6);
  animation: float 4.5s ease-in-out infinite;
}

.preview-img {
  width: 340px;
  max-width: 100%;
  height: auto;
  object-fit: contain;
  filter: drop-shadow(0 16px 40px rgba(42, 36, 32, 0.18));
}

.preview-caption {
  margin-top: var(--spacing-3);
}

.caption-title {
  font-size: var(--font-size-2xl);
  color: var(--color-primary);
  letter-spacing: 4px;
  margin-bottom: var(--spacing-2);
}
.caption-meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}

/* ============================================================
   技术链路
   ============================================================ */
.flow-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--spacing-4);
  margin-top: var(--spacing-4);
  position: relative;
}

.flow-step {
  position: relative;
  text-align: center;
  padding: var(--spacing-6) var(--spacing-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  animation: fadeInUp 0.6s var(--easing-standard) both;
  transition: all var(--transition-normal);
}
.flow-step:hover {
  transform: translateY(-4px);
  border-color: var(--color-accent-light);
  box-shadow: var(--shadow-md);
}

.flow-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin: 0 auto var(--spacing-4);
  background: linear-gradient(135deg, rgba(45, 74, 72, 0.08), rgba(201, 123, 90, 0.08));
  border-radius: var(--radius-xl);
}

.icon-text {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  color: var(--color-primary);
  font-weight: 600;
}

.flow-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-2);
  letter-spacing: 2px;
}

.flow-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.flow-arrow {
  position: absolute;
  top: 50%;
  right: -16px;
  transform: translateY(-50%);
  color: var(--color-accent);
  font-size: 20px;
  font-weight: 300;
  z-index: 2;
  background: var(--color-surface);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-light);
}

/* ============================================================
   四个使用场景
   ============================================================ */
.scene-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-6);
}

.scene-card {
  padding: var(--spacing-8);
  background: var(--color-surface);
  border-left: 4px solid var(--color-accent);
  border-radius: var(--radius-xl);
  border-top: 1px solid var(--color-border-light);
  border-right: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
  transition: all var(--transition-normal);
}
.scene-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-left-color: var(--color-primary);
}

.scene-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.scene-num {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  color: var(--color-accent);
  font-weight: 700;
  line-height: 1;
  opacity: 0.5;
  letter-spacing: 2px;
}

.scene-title {
  font-size: var(--font-size-xl);
  color: var(--color-primary);
  letter-spacing: 4px;
  margin-bottom: 2px;
  font-weight: 600;
}

.scene-for {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}

.scene-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.9;
  margin-bottom: var(--spacing-5);
}

.scene-quote {
  position: relative;
  padding: var(--spacing-4) var(--spacing-6);
  background: rgba(201, 123, 90, 0.06);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-base);
  color: var(--color-accent-dark);
  font-style: italic;
  line-height: 1.9;
  margin: 0 0 var(--spacing-3);
}
.quote-mark {
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  color: var(--color-accent);
  opacity: 0.5;
  margin-right: 4px;
  line-height: 0;
  vertical-align: -8px;
}
.quote-mark.end {
  margin-left: 4px;
  vertical-align: -4px;
}

.scene-byline {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  text-align: right;
}

/* ============================================================
   价值三卡
   ============================================================ */
.value-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-6);
}

.value-card {
  padding: var(--spacing-10) var(--spacing-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  text-align: center;
  transition: all var(--transition-normal);
}
.value-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-accent-light);
}

.value-num {
  font-family: var(--font-family-display);
  font-size: var(--font-size-4xl);
  color: var(--color-accent);
  font-weight: 700;
  margin-bottom: var(--spacing-3);
  letter-spacing: 4px;
}

.value-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  color: var(--color-primary);
  margin-bottom: var(--spacing-4);
  font-weight: 600;
  letter-spacing: 2px;
}

.value-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.9;
}

/* ============================================================
   非遗工作室合作
   ============================================================ */
.heritage-panel {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: var(--spacing-12);
  padding: var(--spacing-16);
  background: linear-gradient(135deg, var(--color-primary) 0%, #1e3533 100%);
  color: #fff;
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-xl);
  position: relative;
  overflow: hidden;
}

.heritage-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 80%, rgba(201, 123, 90, 0.25), transparent 50%),
    radial-gradient(circle at 85% 20%, rgba(212, 165, 116, 0.15), transparent 50%);
  pointer-events: none;
}

.heritage-left {
  position: relative;
  z-index: 1;
}

.heritage-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-secondary);
  font-family: var(--font-family-mono);
  letter-spacing: 3px;
  margin-bottom: var(--spacing-6);
}
.heritage-kicker .kicker-dot {
  width: 6px;
  height: 6px;
  background: var(--color-secondary);
  border-radius: 50%;
}

.heritage-title {
  font-family: var(--font-family-display);
  font-size: clamp(28px, 3.5vw, 42px);
  line-height: 1.5;
  letter-spacing: 3px;
  margin-bottom: var(--spacing-6);
  font-weight: 700;
}

.heritage-desc {
  font-size: var(--font-size-base);
  line-height: 2;
  color: rgba(245, 240, 232, 0.85);
  margin-bottom: var(--spacing-8);
}

.heritage-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-8);
}

.pill {
  display: inline-block;
  padding: 6px 14px;
  background: rgba(201, 123, 90, 0.25);
  color: #f3d4c1;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}

.heritage-cta {
  margin-top: var(--spacing-6);
}

/* ======= 右侧数据卡 ======= */
.heritage-right {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-4);
  align-content: center;
}

.heritage-stat {
  padding: var(--spacing-6);
  background: rgba(255, 253, 249, 0.06);
  border: 1px solid rgba(255, 253, 249, 0.12);
  border-radius: var(--radius-xl);
  transition: all var(--transition-normal);
}
.heritage-stat:hover {
  background: rgba(255, 253, 249, 0.1);
  transform: translateY(-2px);
}

.h-num {
  font-family: var(--font-family-display);
  font-size: clamp(32px, 4vw, 48px);
  color: var(--color-secondary);
  font-weight: 700;
  line-height: 1;
  margin-bottom: var(--spacing-3);
  letter-spacing: 2px;
}
.h-num .percent {
  font-size: 0.5em;
  margin-left: 2px;
}

.h-label {
  font-size: var(--font-size-sm);
  color: rgba(245, 240, 232, 0.75);
  line-height: 1.6;
  letter-spacing: 0.5px;
}

/* ============================================================
   Footer
   ============================================================ */
.footer {
  padding: var(--spacing-10) var(--spacing-8);
  border-top: 1px solid var(--color-border-light);
  margin-top: var(--spacing-12);
  background: linear-gradient(180deg, transparent, rgba(212, 165, 116, 0.04));
}

.footer-inner {
  max-width: var(--container-xl);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-4);
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.footer-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  font-weight: 700;
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(45, 74, 72, 0.3);
}

.footer-name {
  font-size: var(--font-size-lg);
  color: var(--color-primary);
  letter-spacing: 3px;
  font-weight: 600;
}

.footer-slogan {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  margin-top: 2px;
}

.footer-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}

/* ============================================================
   响应式
   ============================================================ */
@media (max-width: 1100px) {
  .hero {
    grid-template-columns: 1fr;
    text-align: center;
    padding: var(--spacing-16) var(--spacing-6);
  }
  .hero-lead { margin-left: auto; margin-right: auto; }
  .hero-cta { justify-content: center; }
  .hero-stats { margin-left: auto; margin-right: auto; }
  .hero-visual { min-height: 400px; }
  .hero-ceramic-img { width: 280px; }

  .problem-grid { grid-template-columns: 1fr; }
  .flow-grid { grid-template-columns: repeat(2, 1fr); }
  .flow-arrow { display: none; }
  .scene-grid { grid-template-columns: 1fr; }
  .value-grid { grid-template-columns: 1fr; }
  .heritage-panel { grid-template-columns: 1fr; padding: var(--spacing-10); }
  .heritage-right { grid-template-columns: repeat(2, 1fr); }
  .demo-panel { grid-template-columns: 1fr; padding: var(--spacing-8); }

  .only-lg { display: none; }
}

@media (max-width: 640px) {
  .hero-stats {
    gap: var(--spacing-3);
    padding: var(--spacing-4);
    flex-wrap: wrap;
    justify-content: center;
  }
  .stat-sep { display: none; }
  .flow-grid { grid-template-columns: 1fr; }
  .heritage-right { grid-template-columns: 1fr; }
  .visual-chip { display: none; }
  .visual-ring { width: 320px; height: 320px; }
}
</style>
