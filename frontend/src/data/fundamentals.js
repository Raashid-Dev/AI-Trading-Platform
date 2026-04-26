// Real reported quarterly data (FY25 actuals) — static reference
// Sources: NSE filings, company IR pages

export const FUNDAMENTALS = {
  NIFTY: {
    type: 'index', fullName: 'NIFTY 50 Index', sector: 'Broad Market',
    pe: 22.4, pbv: 3.8, divYield: 1.2,
    description: 'Benchmark index of 50 large-cap NSE-listed companies across 13 sectors.',
    revenue: null,
  },
  BANKNIFTY: {
    type: 'index', fullName: 'Bank Nifty Index', sector: 'Banking',
    pe: 14.2, pbv: 2.3, divYield: 1.8,
    description: 'Index of the most liquid and large-cap banking stocks listed on NSE.',
    revenue: null,
  },
  RELIANCE: {
    type: 'stock', fullName: 'Reliance Industries Ltd', sector: 'Conglomerate',
    pe: 26.8, pbv: 2.4, divYield: 0.3, marketCap: '17.4L Cr', employees: '2,36,334',
    description: 'India\'s largest company by market cap, spanning O2C, telecom (Jio), and retail.',
    revenue: [
      { q: 'Q1 FY25', rev: 231971, net: 15138 },
      { q: 'Q2 FY25', rev: 235481, net: 16563 },
      { q: 'Q3 FY25', rev: 243042, net: 18540 },
      { q: 'Q4 FY25', rev: 264678, net: 19407 },
    ],
  },
  TCS: {
    type: 'stock', fullName: 'Tata Consultancy Services', sector: 'IT Services',
    pe: 23.1, pbv: 11.8, divYield: 1.8, marketCap: '8.7L Cr', employees: '6,07,000',
    description: 'India\'s largest IT services company; consistent dividend payer with global presence.',
    revenue: [
      { q: 'Q1 FY25', rev: 62613, net: 12040 },
      { q: 'Q2 FY25', rev: 63973, net: 11909 },
      { q: 'Q3 FY25', rev: 63973, net: 12380 },
      { q: 'Q4 FY25', rev: 63437, net: 12224 },
    ],
  },
  INFY: {
    type: 'stock', fullName: 'Infosys Limited', sector: 'IT Services',
    pe: 21.5, pbv: 7.4, divYield: 2.1, marketCap: '6.5L Cr', employees: '3,17,000',
    description: 'Second largest Indian IT firm; strong in cloud, digital and enterprise AI services.',
    revenue: [
      { q: 'Q1 FY25', rev: 38994, net: 6368 },
      { q: 'Q2 FY25', rev: 40986, net: 6506 },
      { q: 'Q3 FY25', rev: 41764, net: 6806 },
      { q: 'Q4 FY25', rev: 40925, net: 7033 },
    ],
  },
  HDFCBANK: {
    type: 'stock', fullName: 'HDFC Bank Limited', sector: 'Private Banking',
    pe: 17.3, pbv: 2.8, divYield: 1.2, marketCap: '12.1L Cr', employees: '2,14,000',
    description: 'India\'s largest private sector bank by assets; known for asset quality and retail franchise.',
    revenue: [
      { q: 'Q1 FY25', rev: 68431, net: 16175 },
      { q: 'Q2 FY25', rev: 71455, net: 16821 },
      { q: 'Q3 FY25', rev: 73957, net: 17654 },
      { q: 'Q4 FY25', rev: 75390, net: 17617 },
    ],
  },
  ICICIBANK: {
    type: 'stock', fullName: 'ICICI Bank Limited', sector: 'Private Banking',
    pe: 16.8, pbv: 3.1, divYield: 0.8, marketCap: '8.6L Cr', employees: '1,48,000',
    description: 'Fast-growing private bank with strong retail, SME, and digital banking presence.',
    revenue: [
      { q: 'Q1 FY25', rev: 38765, net: 10708 },
      { q: 'Q2 FY25', rev: 40499, net: 11792 },
      { q: 'Q3 FY25', rev: 41510, net: 11792 },
      { q: 'Q4 FY25', rev: 43170, net: 12630 },
    ],
  },
};
