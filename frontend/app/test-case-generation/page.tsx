'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { InputPage } from '@/testCase Frontend';

function TestCaseGenerationRouter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams?.get('projectId');

  useEffect(() => {
    // If no explicit projectId is passed, redirect to Application Projects dashboard
    if (!projectId) {
      router.replace('/dashboard');
    }
  }, [projectId, router]);

  if (!projectId) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return <InputPage />;
}

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      }
    >
      <TestCaseGenerationRouter />
    </Suspense>
  );
}
