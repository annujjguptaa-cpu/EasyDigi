export default function CustomerHome() {
  return (
    <div className="min-h-screen bg-paper text-ink flex items-center justify-center p-6">
      <div className="max-w-md w-full border border-hairline bg-surface p-8 text-center space-y-4">
        <h1 className="text-xl font-serif font-bold">EasyDigi Customer Portal</h1>
        <p className="text-xs text-ink/70">
          This portal is accessed via secure single-use links issued by your lending institution.
        </p>
        <div className="text-[11px] font-mono p-2 bg-paper border border-hairline text-ink/60">
          Format: /w/[token]
        </div>
      </div>
    </div>
  );
}
