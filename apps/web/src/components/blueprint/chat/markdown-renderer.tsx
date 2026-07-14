import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import { cn } from '@/lib/utils';

/**
 * Sanitize schema extending the default: allow `<span class="highlight-mark">`
 * (the yellow-marker widget from the chat_formatting_widgets skill) while still
 * stripping scripts, event handlers, and every other unsafe tag/attr from the
 * model-authored markdown.
 */
const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    span: [...(defaultSchema.attributes?.span ?? []), 'className'],
  },
};

/**
 * Markdown renderer for assistant/admin bubbles. A slimmed stand-in for the
 * portal's `~/components/app/MarkdownRenderer` — typography matched to the
 * source: base `text-xs leading-[1.333em] tracking-[-0.03em]` (same size as the
 * user bubble), with the source's per-element sizes.
 */
export function MarkdownRenderer({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'text-xs font-normal leading-[1.333em] tracking-[-0.03em] text-slate-900',
        '[&_p]:mb-3 last:[&_p]:mb-0',
        '[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5',
        '[&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5',
        '[&_li]:pl-1 [&_li]:mb-1',
        '[&_a]:font-medium [&_a]:text-primary [&_a]:underline',
        '[&_code]:rounded [&_code]:border [&_code]:border-slate-200 [&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[10px] [&_code]:leading-[1.4em]',
        '[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-slate-900 [&_pre]:p-4 [&_pre]:font-mono [&_pre]:text-[10px] [&_pre]:leading-[1.4em] [&_pre]:text-slate-100',
        '[&_pre_code]:border-0 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-slate-100',
        '[&_h1]:mt-6 [&_h1]:mb-4 [&_h1]:border-b [&_h1]:pb-2 [&_h1]:text-lg [&_h1]:font-bold first:[&_h1]:mt-0',
        '[&_h2]:mt-6 [&_h2]:mb-3 [&_h2]:text-base [&_h2]:font-semibold first:[&_h2]:mt-0',
        '[&_h3]:mt-5 [&_h3]:mb-2 [&_h3]:text-sm [&_h3]:font-semibold first:[&_h3]:mt-0',
        '[&_h4]:mt-4 [&_h4]:mb-2 [&_h4]:text-xs [&_h4]:font-semibold first:[&_h4]:mt-0',
        '[&_h5]:mt-3 [&_h5]:mb-1.5 [&_h5]:text-[10px] [&_h5]:font-semibold first:[&_h5]:mt-0',
        '[&_h6]:mt-3 [&_h6]:mb-1.5 [&_h6]:text-[10px] [&_h6]:font-semibold [&_h6]:uppercase first:[&_h6]:mt-0',
        '[&_blockquote]:my-4 [&_blockquote]:border-l-4 [&_blockquote]:pl-4 [&_blockquote]:text-[10px] [&_blockquote]:italic [&_blockquote]:leading-[1.4em] [&_blockquote]:opacity-90',
        '[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs',
        '[&_th]:px-4 [&_th]:py-2.5 [&_th]:text-left [&_th]:text-[10px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[-0.03em]',
        '[&_td]:px-4 [&_td]:py-2.5 [&_td]:text-xs',
        '[&_.highlight-mark]:rounded [&_.highlight-mark]:bg-yellow-200 [&_.highlight-mark]:px-1 [&_.highlight-mark]:py-0.5 [&_.highlight-mark]:font-medium [&_.highlight-mark]:text-slate-900 [&_.highlight-mark]:[box-decoration-break:clone] [&_.highlight-mark]:[-webkit-box-decoration-break:clone]',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
