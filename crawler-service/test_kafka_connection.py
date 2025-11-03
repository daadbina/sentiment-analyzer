"""Test Kafka connection."""
import socket
import time

def test_kafka_connection():
    """Test if Kafka is accessible."""
    host = "localhost"
    port = 9092
    
    print(f"Testing Kafka connection to {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Kafka is accessible on {host}:{port}")
            return True
        else:
            print(f"❌ Kafka is NOT accessible on {host}:{port}")
            print(f"   Error code: {result}")
            return False
    except Exception as e:
        print(f"❌ Error testing Kafka: {str(e)}")
        return False

if __name__ == "__main__":
    test_kafka_connection()

