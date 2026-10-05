Pod::Spec.new do |s|
 s.name='FlashDepth'; s.version='0.1.0'; s.summary='One-shot Core ML depth for FlashLook'; s.description=s.summary
 s.license='MIT'; s.author='FlashLook'; s.homepage='https://github.com/Hagyurid/study'; s.platforms={:ios=>'15.1'}
 s.source={:git=>'https://github.com/Hagyurid/study.git'}; s.static_framework=true
 s.dependency 'ExpoModulesCore'; s.source_files='**/*.{h,m,mm,swift}'
end