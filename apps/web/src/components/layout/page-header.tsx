type PageHeaderProps = {
  title: string;
  description: string;
};

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <header className="border-b border-slate-200 pb-7">
      <h1 className="text-3xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-4xl">
        {title}
      </h1>
      <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{description}</p>
    </header>
  );
}
