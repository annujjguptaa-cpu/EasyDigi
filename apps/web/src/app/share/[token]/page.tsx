import { redirect } from 'next/navigation';

export default function ShareAlias({ params }: { params: { token: string } }) {
  redirect(`/c/${params.token}`);
}
