import { Suspense } from 'react';
import { ReportsPage } from '@/testCase Frontend';

export const metadata = {
  title: 'Execution Reports – Application Testing Platform',
  description: 'View Playwright test execution results, pass/fail status, and technical verification evidence.',
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
      <ReportsPage />
    </Suspense>
  );
}
