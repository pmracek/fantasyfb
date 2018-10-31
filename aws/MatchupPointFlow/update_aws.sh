sudo rm -r awspkg/*
sudo /opt/conda/bin/pip install -r requirements.txt -t awspkg
sudo chmod 777 awspkg/*
find "awspkg/" -name "*.so" | xargs strip
cp *.py awspkg
pushd awspkg
rm ../MatchupPointFlow_ChartsDeploy.zip
zip -r -9  ../MatchupPointFlow_ChartsDeploy.zip .
popd
aws s3 cp MatchupPointFlow_ChartsDeploy.zip s3://pmraceklambdacode/
