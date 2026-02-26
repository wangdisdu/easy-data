import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked 选项，优化流式渲染体验
marked.setOptions({
  breaks: true, // 支持 GitHub 风格的换行
  gfm: true, // 启用 GitHub 风格的 Markdown
})

/**
 * 将 Markdown 文本渲染为安全的 HTML
 * 支持流式渲染（处理不完整的 Markdown 语法）
 * 
 * @param markdown - Markdown 文本内容
 * @returns 安全的 HTML 字符串
 */
export function renderMarkdown(markdown: string): string {
  if (!markdown) return ''
  
  try {
    // 对于流式输出，可能存在不完整的代码块，需要特殊处理
    // 检查是否有未闭合的代码块（``` 的数量为奇数）
    const codeBlockMatches = markdown.match(/```/g)
    const hasUnclosedCodeBlock = codeBlockMatches && codeBlockMatches.length % 2 !== 0
    
    let processedMarkdown = markdown
    
    // 如果有未闭合的代码块，需要特殊处理以支持流式渲染
    if (hasUnclosedCodeBlock) {
      // 找到最后一个 ``` 的位置
      const lastCodeBlockIndex = markdown.lastIndexOf('```')
      const afterLastCodeBlock = markdown.substring(lastCodeBlockIndex + 3)
      
      // 如果后面还有内容，说明代码块未闭合（正在流式输出中）
      if (afterLastCodeBlock.trim()) {
        // 为了正确渲染，临时添加闭合标记
        // 这样 marked 可以正确解析，同时不影响后续内容的追加
        processedMarkdown = markdown + '\n```'
      }
    }
    
    // 使用 marked 解析 Markdown
    // marked 可以处理不完整的 Markdown，但为了更好的流式体验，我们做了上述处理
    const html = marked.parse(processedMarkdown) as string
    
    // 使用 DOMPurify 清理 HTML，防止 XSS 攻击
    const cleanHtml = DOMPurify.sanitize(html, {
      // 允许代码高亮相关的标签和属性
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img', 'hr',
        'span', 'div'
      ],
      ALLOWED_ATTR: ['href', 'title', 'alt', 'class', 'target', 'rel'],
      // 允许代码块中的样式（用于语法高亮）
      ALLOW_DATA_ATTR: false,
    })
    
    return cleanHtml
  } catch (error) {
    console.error('Markdown 渲染错误:', error)
    // 如果渲染失败，返回转义后的纯文本
    return DOMPurify.sanitize(
      markdown
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
    )
  }
}

