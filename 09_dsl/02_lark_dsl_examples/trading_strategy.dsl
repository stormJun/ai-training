STRATEGY "趋势突破策略" VERSION 2.1
AUTHOR "张交易员"
CAPITAL $100000
RISK_PER_TRADE 2%

# ==================== 入场条件 ====================
ENTRY_RULE "突破买入"
  WHEN price > SMA(20) AND volume > AVG_VOLUME * 1.5
  AND RSI(14) < 70
  THEN BUY AT market_price
       SIZE = CAPITAL * RISK_PER_TRADE / ATR(14)
       STOP_LOSS = entry_price - 2 * ATR(14)
       TAKE_PROFIT = entry_price + 3 * ATR(14)

ENTRY_RULE "支撑反弹"
  WHEN price TOUCHES SUPPORT_LEVEL
  AND MACD_HISTOGRAM > 0
  THEN BUY AT limit_price = SUPPORT_LEVEL * 1.001
       SIZE = $5000
       STOP_LOSS = SUPPORT_LEVEL * 0.98

# ==================== 出场条件 ====================
EXIT_RULE "止损出场"
  WHEN price < position.stop_loss
  THEN SELL ALL AT market_price URGENCY high

EXIT_RULE "获利了结"
  WHEN price > position.take_profit
  OR holding_time > 5 days AND profit_pct > 1.5%
  THEN SELL 50% AT market_price
       ADJUST_STOP_LOSS TO entry_price

EXIT_RULE "趋势反转"
  WHEN price < SMA(20) AND MACD_SIGNAL == "bearish"
  THEN SELL ALL AT market_price

# ==================== 风控规则 ====================
RISK_CONTROL
  MAX_POSITIONS = 5
  MAX_DAILY_LOSS = $2000
  MAX_POSITION_SIZE = $20000
  BLACKLIST = ["SPAC股票", "仙股"]

# ==================== 时间控制 ====================
TRADING_HOURS
  ACTIVE_BETWEEN 09:30 AND 15:30 TIMEZONE "America/New_York"
  AVOID_FIRST 5min
  AVOID_LAST 10min
