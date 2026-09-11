import { Suspense } from 'react';
import { ResultsPage } from '@/testCase Frontend';

export const metadata = {
  title: 'Test Cases & Scenarios – Application Testing Platform',
  description: 'Verified test scenarios and test cases mapped to crawled UI elements.',
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
      <ResultsPage />
    </Suspense>
  );
}
