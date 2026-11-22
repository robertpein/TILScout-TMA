/*
 * Export of TMA cores from QuPath as uncompressed .tif images (input for TILScout-TMA)
 *
 * Run in QuPath (Automate > Script editor) on a TMA slide after dearraying
 * (TMA > TMA dearrayer). Every TMA core of the current image is exported as an RGB .tif
 * named <slide name>_<core name>.tif, e.g. AMP_TMA_01_D-2.tif.
 *
 * The second argument of RegionRequest.createInstance() is a downsample factor relative
 * to the full-resolution scan, not a pixel size. For a 40x scan (about 0.25 um/pixel),
 * a downsample of 2 gives about 0.5 um/pixel, i.e. about 20x.
 * Used with QuPath 0.6.0.
 */
import qupath.lib.regions.RegionRequest
import javax.imageio.ImageIO
import java.awt.image.BufferedImage
import java.nio.file.Paths

// Downsample factor (2 = about 20x for a 40x scan)
double downsample = 2

// Output folder inside the QuPath project
def outputDir = buildFilePath(PROJECT_BASE_DIR, 'exported_tma_cores_20x')
mkdirs(outputDir)

// Image data and server
def imageData = getCurrentImageData()
def server = imageData.getServer()
def imagePath = server.getPath()

// Slide name without extension (e.g. AMP_TMA_01)
def imageName = Paths.get(imagePath).getFileName().toString().replaceFirst(/[.][^.]+$/, "")

// All TMA cores of the current image
def tmaCores = getCurrentHierarchy().getRootObject().getDescendantObjects().findAll { it.isTMACore() }

print "Exporting ${tmaCores.size()} TMA cores (downsample ${downsample})..."

for (core in tmaCores) {
    def coreName = core.getName() ?: "core_" + core.getID().toString().take(8)
    def region = RegionRequest.createInstance(imagePath, downsample, core.getROI())
    BufferedImage img = server.readRegion(region)

    def filename = imageName + "_" + coreName + ".tif"
    def outputPath = buildFilePath(outputDir, filename)

    ImageIO.write(img, "TIFF", new File(outputPath))
}

print "Done. Cores exported to: " + outputDir
