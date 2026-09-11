import { Suspense } from 'react';
import { ReviewPage } from '@/testCase Frontend';

export const metadata = {
  title: 'Manual Review – Application Testing Platform',
  description: 'Manual review and refinement for generated test scenarios and cases.',
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
      <ReviewPage />
    </Suspense>
  );
}
