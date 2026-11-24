const storage = multer.diskStorage({
  destination: 'uploads/',
  filename: (_req, file, cb) => cb(null, file.originalname),
});
