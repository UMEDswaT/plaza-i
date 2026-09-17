import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['tj', 'ru', 'en'],
  defaultLocale: 'tj',
  localePrefix: 'always'
});

export type Locale = (typeof routing.locales)[number];
