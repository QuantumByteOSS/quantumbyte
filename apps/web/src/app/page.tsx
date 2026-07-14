import { redirect } from 'next/navigation';

export default function Index() {
  // Temporary redirect (307): auth lands here in phase 2.
  redirect('/dashboard/project');
}
