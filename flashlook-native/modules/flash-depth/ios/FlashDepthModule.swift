import ExpoModulesCore
import CoreML
import UIKit
import CoreVideo

public class FlashDepthModule: Module {
  public func definition() -> ModuleDefinition {
    Name("FlashDepth")
    AsyncFunction("analyze") { (uri: String) -> [String: Any] in
      guard let url = URL(string: uri), let data = try? Data(contentsOf: url),
            let image = UIImage(data: data), let cg = image.cgImage else {
        throw NSError(domain:"FlashDepth",code:1,userInfo:[NSLocalizedDescriptionKey:"Image decode failed"])
      }
      guard let modelURL = Bundle.main.url(forResource:"DepthAnythingV2SmallF16P6",withExtension:"mlmodelc") else {
        throw NSError(domain:"FlashDepth",code:2,userInfo:[NSLocalizedDescriptionKey:"Core ML depth model is not bundled"])
      }
      let cfg=MLModelConfiguration(); cfg.computeUnits = .all
      let model=try MLModel(contentsOf:modelURL,configuration:cfg)
      let inputName=model.modelDescription.inputDescriptionsByName.keys.first!
      let desc=model.modelDescription.inputDescriptionsByName[inputName]!
      guard let constraint=desc.imageConstraint else { throw NSError(domain:"FlashDepth",code:3,userInfo:nil) }
      let pb=try Self.pixelBuffer(cg,width:constraint.pixelsWide,height:constraint.pixelsHigh)
      let provider=try MLDictionaryFeatureProvider(dictionary:[inputName:MLFeatureValue(pixelBuffer:pb)])
      let prediction=try model.prediction(from:provider)
      guard let outName=model.modelDescription.outputDescriptionsByName.first(where:{$0.value.type == .multiArray})?.key,
            let arr=prediction.featureValue(for:outName)?.multiArrayValue else {
        throw NSError(domain:"FlashDepth",code:4,userInfo:[NSLocalizedDescriptionKey:"Depth output unavailable"])
      }
      let count=arr.count; var mn=Float.greatestFiniteMagnitude,mx = -Float.greatestFiniteMagnitude
      var vals=[Float](repeating:0,count:count)
      for i in 0..<count { let x=arr[i].floatValue; vals[i]=x; mn=min(mn,x); mx=max(mx,x) }
      let range=max(mx-mn,0.000001); var bytes=[UInt8](repeating:0,count:count)
      for i in 0..<count { bytes[i]=UInt8(clamping:Int(((vals[i]-mn)/range*255).rounded())) }
      let shape=arr.shape.map{$0.intValue}; let h=shape.count>1 ? shape[shape.count-2] : 1; let w=shape.last ?? count
      return ["width":w,"height":h,"depth":Data(bytes).base64EncodedString()]
    }
  }
  static func pixelBuffer(_ image:CGImage,width:Int,height:Int)throws->CVPixelBuffer{
    var pb:CVPixelBuffer?; let attrs=[kCVPixelBufferCGImageCompatibilityKey:true,kCVPixelBufferCGBitmapContextCompatibilityKey:true] as CFDictionary
    CVPixelBufferCreate(kCFAllocatorDefault,width,height,kCVPixelFormatType_32BGRA,attrs,&pb)
    guard let b=pb else { throw NSError(domain:"FlashDepth",code:5,userInfo:nil) }
    CVPixelBufferLockBaseAddress(b,[]); defer{CVPixelBufferUnlockBaseAddress(b,[])}
    let ctx=CGContext(data:CVPixelBufferGetBaseAddress(b),width:width,height:height,bitsPerComponent:8,bytesPerRow:CVPixelBufferGetBytesPerRow(b),space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue|CGBitmapInfo.byteOrder32Little.rawValue)!
    ctx.interpolationQuality = .high; ctx.draw(image,in:CGRect(x:0,y:0,width:width,height:height)); return b
  }
}