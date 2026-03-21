import mountWidget from './widget/mountWidget'

mountWidget(document.getElementById('root')!, {
  apiBase: 'http://localhost:5000',
  indexPath: './docs',
  theme: 'dark',
  tokenCount: 8192,
})