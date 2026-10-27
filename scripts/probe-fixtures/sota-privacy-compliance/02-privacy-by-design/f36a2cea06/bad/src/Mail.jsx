export function MailBody({ message }) {
  return <div dangerouslySetInnerHTML={{ __html: message.body_html }} />;
}
