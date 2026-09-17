import Link from 'next/link';

type Props = {
  params: Promise<{
    locale: string;
  }>;
};

const content = {
  tj: {
    nav: ['Асосӣ', 'Дар бораи мо', 'Хизматрасониҳо', 'Портфолио', 'Нархҳо', 'Тамос'],
    eyebrow: 'АРХИТЕКТУРА • ДИЗАЙН • СОХТМОН',
    title1: 'МО ФАЗОРО',
    title2: 'БА МЕЪМОРӢ',
    title3: 'ТАБДИЛ МЕДИҲЕМ.',
    text: 'Лоиҳакашии меъморӣ, дизайн ва назорати муаллифӣ барои объектҳои замонавӣ дар Душанбе.',
    project: 'ФАРМОИШИ ЛОИҲА',
    portfolio: 'ДИДАНИ ПОРТФОЛИО',
    about: 'ДАР БОРАИ МО',
    aboutTitle: 'ПЛАЗА-И — меъморӣ бо масъулият.',
    aboutText:
      'Мо лоиҳаҳои меъморӣ ва дизайнро аз идея то татбиқ таҳия намуда, сифати иҷрои онҳоро тавассути назорати муаллифӣ пайгирӣ мекунем.',
    services: 'ХИЗМАТРАСОНИҲО',
    service1: 'Лоиҳакашии меъморӣ',
    service2: 'Дизайни интерьер',
    service3: 'Назорати муаллифӣ',
    portfolioTitle: 'ЛОИҲАҲОИ МО',
    contactTitle: 'ЛОИҲАИ НАВ ДОРЕД?',
    contactText: 'Бо мо тамос гиред. Мо идеяи шуморо ба лоиҳаи воқеӣ табдил медиҳем.',
    contactButton: 'БО МО ТАМОС ГИРЕД'
  },

  ru: {
    nav: ['Главная', 'О нас', 'Услуги', 'Портфолио', 'Цены', 'Контакты'],
    eyebrow: 'АРХИТЕКТУРА • ДИЗАЙН • СТРОИТЕЛЬСТВО',
    title1: 'МЫ ПРЕВРАЩАЕМ',
    title2: 'ПРОСТРАНСТВО',
    title3: 'В АРХИТЕКТУРУ.',
    text: 'Архитектурное проектирование, дизайн и авторский надзор современных объектов в Душанбе.',
    project: 'ЗАКАЗАТЬ ПРОЕКТ',
    portfolio: 'СМОТРЕТЬ ПОРТФОЛИО',
    about: 'О НАС',
    aboutTitle: 'ПЛАЗА-И — архитектура с ответственностью.',
    aboutText:
      'Мы разрабатываем архитектурные и дизайнерские проекты от идеи до реализации и контролируем качество исполнения посредством авторского надзора.',
    services: 'УСЛУГИ',
    service1: 'Архитектурное проектирование',
    service2: 'Дизайн интерьера',
    service3: 'Авторский надзор',
    portfolioTitle: 'НАШИ ПРОЕКТЫ',
    contactTitle: 'ЕСТЬ НОВЫЙ ПРОЕКТ?',
    contactText: 'Свяжитесь с нами. Мы превратим вашу идею в реальный проект.',
    contactButton: 'СВЯЗАТЬСЯ С НАМИ'
  },

  en: {
    nav: ['Home', 'About', 'Services', 'Portfolio', 'Pricing', 'Contacts'],
    eyebrow: 'ARCHITECTURE • DESIGN • CONSTRUCTION',
    title1: 'WE TRANSFORM',
    title2: 'SPACE INTO',
    title3: 'ARCHITECTURE.',
    text: 'Architectural design, interior design and author supervision for contemporary projects in Dushanbe.',
    project: 'START A PROJECT',
    portfolio: 'VIEW PORTFOLIO',
    about: 'ABOUT US',
    aboutTitle: 'PLAZA-I — architecture with responsibility.',
    aboutText:
      'We develop architectural and interior projects from concept to implementation and supervise construction quality.',
    services: 'SERVICES',
    service1: 'Architectural Design',
    service2: 'Interior Design',
    service3: 'Author Supervision',
    portfolioTitle: 'SELECTED PROJECTS',
    contactTitle: 'HAVE A NEW PROJECT?',
    contactText: 'Contact us. We will turn your idea into a real project.',
    contactButton: 'CONTACT US'
  }
} as const;

export default async function HomePage({params}: Props) {
  const {locale} = await params;
  const lang = locale === 'ru' || locale === 'en' ? locale : 'tj';
  const t = content[lang];

  return (
    <main className="min-h-screen bg-[#090909] text-white">

      <header className="fixed left-0 top-0 z-50 w-full border-b border-white/10 bg-black/70 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-10">
          <Link href={`/${lang}`} className="text-2xl font-black tracking-tight">
            ПЛАЗА-И
          </Link>

          <nav className="hidden items-center gap-7 text-sm text-white/70 lg:flex">
            <a href="#home" className="transition hover:text-white">{t.nav[0]}</a>
            <a href="#about" className="transition hover:text-white">{t.nav[1]}</a>
            <a href="#services" className="transition hover:text-white">{t.nav[2]}</a>
            <a href="#portfolio" className="transition hover:text-white">{t.nav[3]}</a>
            <a href="#contact" className="transition hover:text-white">{t.nav[5]}</a>
          </nav>

          <div className="flex items-center gap-3 text-xs font-bold">
            <Link href="/tj" className={lang === 'tj' ? 'text-white' : 'text-white/40'}>TJ</Link>
            <span className="text-white/20">/</span>
            <Link href="/ru" className={lang === 'ru' ? 'text-white' : 'text-white/40'}>RU</Link>
            <span className="text-white/20">/</span>
            <Link href="/en" className={lang === 'en' ? 'text-white' : 'text-white/40'}>EN</Link>
          </div>
        </div>
      </header>

      <section id="home" className="flex min-h-screen items-center border-b border-white/10 px-6 pt-20 lg:px-10">
        <div className="mx-auto w-full max-w-7xl py-24">
          <p className="mb-7 text-xs font-semibold tracking-[0.3em] text-white/50">
            {t.eyebrow}
          </p>

          <h1 className="max-w-6xl text-5xl font-black leading-[0.92] tracking-[-0.05em] sm:text-7xl lg:text-[110px]">
            {t.title1}
            <br />
            <span className="text-white/35">{t.title2}</span>
            <br />
            {t.title3}
          </h1>

          <div className="mt-10 flex max-w-3xl flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <p className="max-w-xl text-base leading-7 text-white/55 sm:text-lg">
              {t.text}
            </p>

            <a
              href="#contact"
              className="shrink-0 bg-white px-7 py-4 text-xs font-black tracking-wider text-black transition hover:bg-white/80"
            >
              {t.project}
            </a>
          </div>
        </div>
      </section>

      <section id="about" className="border-b border-white/10 px-6 py-28 lg:px-10 lg:py-40">
        <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1fr_2fr]">
          <p className="text-xs font-bold tracking-[0.3em] text-white/40">
            01 / {t.about}
          </p>

          <div>
            <h2 className="max-w-4xl text-4xl font-bold leading-tight sm:text-6xl">
              {t.aboutTitle}
            </h2>
            <p className="mt-8 max-w-2xl text-lg leading-8 text-white/50">
              {t.aboutText}
            </p>
          </div>
        </div>
      </section>

      <section id="services" className="border-b border-white/10 px-6 py-28 lg:px-10 lg:py-40">
        <div className="mx-auto max-w-7xl">
          <p className="mb-16 text-xs font-bold tracking-[0.3em] text-white/40">
            02 / {t.services}
          </p>

          {[t.service1, t.service2, t.service3].map((service, index) => (
            <div
              key={service}
              className="group flex items-center justify-between border-t border-white/15 py-8 last:border-b"
            >
              <div className="flex items-center gap-6">
                <span className="text-xs text-white/30">0{index + 1}</span>
                <h3 className="text-2xl font-semibold transition group-hover:translate-x-3 sm:text-4xl">
                  {service}
                </h3>
              </div>
              <span className="text-2xl text-white/30">↗</span>
            </div>
          ))}
        </div>
      </section>

      <section id="portfolio" className="border-b border-white/10 px-6 py-28 lg:px-10 lg:py-40">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-bold tracking-[0.3em] text-white/40">
            03 / PORTFOLIO
          </p>

          <h2 className="mt-6 text-5xl font-black tracking-tight sm:text-7xl">
            {t.portfolioTitle}
          </h2>

          <div className="mt-16 grid gap-5 md:grid-cols-2">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="flex aspect-[4/3] items-end border border-white/10 bg-gradient-to-br from-neutral-800 to-neutral-950 p-7"
              >
                <div>
                  <p className="text-xs tracking-[0.25em] text-white/35">
                    PROJECT 0{item}
                  </p>
                  <p className="mt-2 text-2xl font-semibold">PLAZA-I</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="contact" className="px-6 py-28 lg:px-10 lg:py-40">
        <div className="mx-auto max-w-7xl">
          <p className="text-xs font-bold tracking-[0.3em] text-white/40">
            04 / CONTACT
          </p>

          <h2 className="mt-8 max-w-5xl text-5xl font-black tracking-tight sm:text-8xl">
            {t.contactTitle}
          </h2>

          <p className="mt-8 max-w-xl text-lg leading-8 text-white/50">
            {t.contactText}
          </p>

          <a
            href="tel:+992000000000"
            className="mt-10 inline-block bg-white px-8 py-5 text-sm font-black tracking-wider text-black"
          >
            {t.contactButton} →
          </a>
        </div>
      </section>

      <footer className="border-t border-white/10 px-6 py-8 lg:px-10">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-4 text-xs text-white/35 sm:flex-row">
          <p>© 2026 ПЛАЗА-И ЧДММ</p>
          <p>DUSHANBE, TAJIKISTAN</p>
        </div>
      </footer>

    </main>
  );
}