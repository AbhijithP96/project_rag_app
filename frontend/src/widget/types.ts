export interface WidgetOptions {
    apiBase: string,
    indexPath : string,
    theme?: 'light' | 'dark',
    tokenCount?: number 
}

export type IndexStatus = 'idle' | 'indexing' | 'ready' | 'error'