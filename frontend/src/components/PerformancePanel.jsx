const Tile = ({ label, value, sub, color = 'text-white', accent = false }) => (
  <div className={`rounded-lg p-3.5 ${accent ? 'bg-blue-900/20 border border-blue-700/20' : 'bg-gray-800/50 border border-gray-700/20'}`}>
    <p className={`text-base font-bold font-mono leading-tight ${color}`}>{value}</p>
    {sub && <p className="text-[10px] text-gray-600 mt-0.5">{sub}</p>}
    <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wide">{label}</p>
  </div>
);

const pct = (n) => `${((n || 0) * 100).toFixed(0)}%`;
const pp  = (n, dp = 3) => {
  const v = n || 0;
  return `${v >= 0 ? '+' : ''}${v.toFixed(dp)}%`;
};

export default function PerformancePanel({ performance: p = {}, diagnostics: d = {} }) {

  const winRate    = (p.win_rate || 0) * 100;
  const closed     = p.closed_trades || 0;
  const pf         = d.profit_factor;
  const pfDisplay  = pf == null ? '–' : pf === Infinity || pf > 99 ? '∞' : pf.toFixed(2);

  const winStreakColor  = (d.max_win_streak  || 0) >= 3 ? 'text-green-400' : 'text-white';
  const lossStreakColor = (d.max_loss_streak || 0) >= 3 ? 'text-red-400'   : 'text-white';

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 shadow-lg h-full">

      <div className="flex items-center justify-between mb-4">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
          Performance
        </p>
        {closed > 0 && (
          <span className="text-xs text-gray-600 font-mono">{closed} closed trades</span>
        )}
      </div>

      {closed === 0 ? (
        <p className="text-gray-600 text-sm py-4 text-center">
          Performance metrics will appear after first closed trade
        </p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">

          <Tile
            label="Win Rate"
            value={`${winRate.toFixed(0)}%`}
            sub={`${Math.round((p.win_rate||0) * closed)}/${closed} wins`}
            color={winRate >= 50 ? 'text-green-400' : 'text-red-400'}
          />

          <Tile
            label="Total PnL"
            value={pp(p.total_pnl)}
            color={(p.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
          />

          <Tile
            label="Avg Win"
            value={`+${(p.avg_win || 0).toFixed(3)}%`}
            color="text-green-400"
          />

          <Tile
            label="Avg Loss"
            value={`${(p.avg_loss || 0).toFixed(3)}%`}
            color="text-red-400"
          />

          <Tile
            label="Expectancy"
            value={pp(d.expectancy)}
            color={(d.expectancy || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
            accent
          />

          <Tile
            label="Profit Factor"
            value={pfDisplay}
            color={(pf || 0) >= 1 ? 'text-blue-400' : 'text-orange-400'}
            accent
          />

          <Tile
            label="Win Streak"
            value={d.max_win_streak ?? '–'}
            sub="max consecutive"
            color={winStreakColor}
          />

          <Tile
            label="Loss Streak"
            value={d.max_loss_streak ?? '–'}
            sub="max consecutive"
            color={lossStreakColor}
          />

        </div>
      )}
    </div>
  );
}
