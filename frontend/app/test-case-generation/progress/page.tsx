import { Suspense } from 'react';
import { ProgressPage } from '@/testCase Frontend';

export const metadata = {
  title: 'Generation Progress – Application Testing Platform',
  description: 'Track multi-agent scenario and test case generation in real time.',
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
      <ProgressPage />
    </Suspense>
  );
}
