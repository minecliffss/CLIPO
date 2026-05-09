const fs = require("fs");
const path = require("path");
const sizeOf = require("image-size");

const imagesDir = "/home/daniel/Desktop/Lensora/Images";
const outputDir = path.join(__dirname, "../public");
const outputFile = path.join(outputDir, "images.json");

try {
  const files = fs.readdirSync(imagesDir);
  const imageFiles = files.filter((file) => {
    const ext = path.extname(file).toLowerCase();
    return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"].includes(ext);
  });

  const images = imageFiles.map((file) => {
    const filePath = path.join(imagesDir, file);
    let width = 400;
    let height = 300;

    try {
      const dimensions = sizeOf(filePath);
      if (dimensions && dimensions.width && dimensions.height) {
        width = dimensions.width;
        height = dimensions.height;
      }
    } catch (e) {
      // fallback dimensions
    }

    return {
      name: file,
      src: `/images/${encodeURIComponent(file)}`,
      alt: path.parse(file).name,
      width,
      height,
    };
  });

  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(outputFile, JSON.stringify({ images }, null, 2));
  console.log(`Generated images.json with ${images.length} images`);
} catch (error) {
  console.error("Failed to scan images:", error);
  process.exit(1);
}
