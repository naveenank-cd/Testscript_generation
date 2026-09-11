import { Suspense } from 'react';
import { AutomationPage } from '@/testCase Frontend';

export const metadata = {
  title: 'Automation Runner – Application Testing Platform',
  description: 'Generated Playwright automation test scripts with page object models.',
};

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      }
    >
      <AutomationPage />
    </Suspense>
  );
}
