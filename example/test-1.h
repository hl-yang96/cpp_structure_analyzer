#ifndef TEST1_H
#define TEST1_H

#include <vector>
#include <map>
#include <unordered_set>
#include <unordered_map>
#include <set>
#include <list>
#include <string>
#include <memory>
#include <array>

// Forward declarations
class DatabaseConnection;
struct NetworkConfig;

// Enum definitions
enum class Priority {
    LOW = 0,
    MEDIUM = 1,
    HIGH = 2,
    CRITICAL = 3
};

enum Status {
    INACTIVE,
    ACTIVE,
    PENDING,
    COMPLETED
};

// Simple custom classes
class Point3D {
public:
    double x, y, z;
    
    Point3D(double x = 0.0, double y = 0.0, double z = 0.0) 
        : x(x), y(y), z(z) {}
    
    double distance() const { return 0.0; }
};

class UserInfo {
private:
    std::string username_;
    int user_id_;
    bool is_admin_;
    
public:
    UserInfo(const std::string& name, int id, bool admin = false)
        : username_(name), user_id_(id), is_admin_(admin) {}
    
    const std::string& getUsername() const { return username_; }
    int getUserId() const { return user_id_; }
    bool isAdmin() const { return is_admin_; }
};

// Template class
template<typename T>
class Buffer {
private:
    T* data_;
    size_t size_;
    size_t capacity_;
    
public:
    Buffer(size_t initial_capacity = 10) : data_(nullptr), size_(0), capacity_(initial_capacity) {}
    ~Buffer() { delete[] data_; }
    
    void push(const T& item) {}
    T pop() { return T(); }
    size_t size() const { return size_; }
    bool empty() const { return size_ == 0; }
};

// Nested struct
struct NetworkConfig {
    std::string host;
    int port;
    bool use_ssl;
    std::vector<std::string> allowed_ips;
    
    struct Authentication {
        std::string username;
        std::string password;
        std::vector<std::string> certificates;
        bool two_factor_enabled;
    } auth;
    
    struct Timeouts {
        int connection_timeout;
        int read_timeout;
        int write_timeout;
    } timeouts;
};

// Complex struct with various member types
struct ComplexDataStructure {
    // Basic types
    int id;
    double weight;
    bool is_active;
    char status_code;
    
    // Const members
    const std::string name;
    const int max_connections;
    
    // Pointers
    UserInfo* owner;
    Point3D* location;
    DatabaseConnection* db_connection;
    
    // Smart pointers
    std::shared_ptr<NetworkConfig> network_config;
    std::unique_ptr<Buffer<int>> int_buffer;
    std::weak_ptr<UserInfo> last_modifier;
    
    // Arrays
    int fixed_array[10];
    double coordinates[3];
    char buffer[256];
    
    // STL arrays
    std::array<float, 5> measurements;
    std::array<std::string, 3> tags;
    
    // STL containers - sequential
    std::vector<UserInfo> users;
    std::vector<Point3D*> waypoints;
    std::list<std::string> log_messages;
    std::vector<std::shared_ptr<DatabaseConnection>> db_pool;
    
    // STL containers - associative
    std::map<std::string, int> string_to_int_map;
    std::map<int, UserInfo*> user_registry;
    std::unordered_map<std::string, double> metrics;
    std::multimap<Priority, std::string> priority_tasks;
    
    // STL containers - sets
    std::set<int> unique_ids;
    std::unordered_set<std::string> keywords;
    
    // Nested containers
    std::vector<std::vector<int>> matrix;
    std::map<std::string, std::vector<Point3D>> named_paths;
    std::unordered_map<int, std::map<std::string, double>> nested_metrics;
    
    // Enums
    Priority current_priority;
    Status current_status;
    
    // Function pointers
    int (*callback_function)(int, double);
    void (*error_handler)(const char*);
    
    // Typedef members
    typedef std::map<std::string, std::vector<UserInfo*>> UserGroupMap;
    UserGroupMap user_groups;
    
    // Nested struct instance
    NetworkConfig network_settings;
};

// Additional complex nested structure
struct SystemConfiguration {
    struct DatabaseSettings {
        std::string connection_string;
        int pool_size;
        std::vector<std::string> backup_hosts;
        std::map<std::string, std::string> connection_params;
        
        struct ReplicationConfig {
            bool enabled;
            std::vector<std::string> replica_hosts;
            int sync_interval;
            Priority replication_priority;
        } replication;
    } database;
    
    struct CacheSettings {
        size_t max_memory_mb;
        int ttl_seconds;
        std::unordered_map<std::string, int> cache_policies;
        std::vector<std::pair<std::string, size_t>> cache_partitions;
    } cache;
    
    struct LoggingSettings {
        enum LogLevel { DEBUG, INFO, WARNING, ERROR, FATAL };
        LogLevel min_level;
        std::string log_file_path;
        bool rotate_logs;
        size_t max_file_size_mb;
        std::vector<std::string> log_targets;
    } logging;
    
    // Complex nested containers
    std::map<std::string, std::vector<std::shared_ptr<ComplexDataStructure>>> data_collections;
    std::unordered_map<int, std::unique_ptr<SystemConfiguration>> subsystems;
};

// Global instances for testing
extern ComplexDataStructure* g_main_structure;
extern std::vector<ComplexDataStructure> g_structure_pool;
extern std::map<int, SystemConfiguration> g_system_configs;

#endif // TEST1_H
