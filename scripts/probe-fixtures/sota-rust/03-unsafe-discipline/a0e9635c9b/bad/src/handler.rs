pub fn handle(req: Request) -> &'static str {
    let body: String = req.body_text();
    Box::leak(body.into_boxed_str())
}
