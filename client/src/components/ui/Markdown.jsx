// Minimal, safe renderer for the light markdown the assistant returns:
// paragraphs, "*"/"-" bullets, numbered lists, **bold**, *italic* and `code`.
// It builds React elements (never raw HTML), so model output cannot inject markup.

function renderInline(text, keyPrefix) {
  const parts = []
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g
  let last = 0
  let match
  let index = 0
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const token = match[0]
    const key = `${keyPrefix}-${index++}`
    if (token.startsWith('**')) parts.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    else if (token.startsWith('`')) parts.push(<code key={key}>{token.slice(1, -1)}</code>)
    else parts.push(<em key={key}>{token.slice(1, -1)}</em>)
    last = match.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

export function Markdown({ text }) {
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let list = null
  let paragraph = []

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: 'p', text: paragraph.join(' ') })
    paragraph = []
  }
  const flushList = () => {
    if (list) blocks.push(list)
    list = null
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    const bullet = line.match(/^[*-]\s+(.*)$/)
    const numbered = line.match(/^\d+[.)]\s+(.*)$/)
    const heading = line.match(/^#{1,6}\s+(.*)$/)

    if (!line) {
      flushParagraph()
      flushList()
    } else if (bullet || numbered) {
      flushParagraph()
      const type = bullet ? 'ul' : 'ol'
      if (!list || list.type !== type) {
        flushList()
        list = { type, items: [] }
      }
      list.items.push((bullet || numbered)[1])
    } else if (heading) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'h', text: heading[1] })
    } else {
      flushList()
      paragraph.push(line)
    }
  }
  flushParagraph()
  flushList()

  return (
    <div className="markdown">
      {blocks.map((block, index) => {
        if (block.type === 'p') return <p key={index}>{renderInline(block.text, index)}</p>
        if (block.type === 'h') return <h4 key={index}>{renderInline(block.text, index)}</h4>
        const List = block.type
        return (
          <List key={index}>
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{renderInline(item, `${index}-${itemIndex}`)}</li>
            ))}
          </List>
        )
      })}
    </div>
  )
}
