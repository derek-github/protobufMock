if [ $# -ne 1 ]
then
echo "Usage: .\\"$0" ***.proto"
exit -1
fi

SRC_DIR=$(cd "$(dirname "$0")"; pwd)
DST_DIR=$SRC_DIR
PROTO_FILE=$1

protoc > /dev/null 2>&1
if [ $? -eq 127 ];then
echo "need to install protobuf..."
echo "install..."
tar xzvf protobuf-2.3.0.tar.gz
cd protobuf-2.3.0
./configure ;make ;make install
cd -
fi

protoc -I=$SRC_DIR --python_out=$DST_DIR $SRC_DIR"/"$PROTO_FILE
