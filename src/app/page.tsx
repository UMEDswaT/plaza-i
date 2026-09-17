import {getTranslations} from 'next-intl/server';

export default async function HomePage() {
  const t = await getTranslations('Home');

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-6 text-white">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          {t('title')}
        </h1>

        <p className="mt-4 text-lg text-neutral-300">
          {t('subtitle')}
        </p>
      </div>
    </main>
  );
}