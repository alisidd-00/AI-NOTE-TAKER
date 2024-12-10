cmake_minimum_required(VERSION 3.16)

project(meetingSDKDemo CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
add_definitions(-std=c++11)
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin)

find_package(PkgConfig REQUIRED)
find_package(ZLIB REQUIRED)


include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include/h)


include_directories(/usr/include/glib-2.0/)
include_directories(/usr/include/glib-2.0/glib)
include_directories(/usr/lib/x86_64-linux-gnu/glib-2.0/include/)
include_directories(/usr/lib64/glib-2.0/include/)


link_directories(${CMAKE_CURRENT_SOURCE_DIR}/lib/zoom_meeting_sdk)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/lib/zoom_meeting_sdk/qt_libs)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/lib/zoom_meeting_sdk/qt_libs/Qt/lib)


add_executable(meetingSDKDemo 
              ${CMAKE_CURRENT_SOURCE_DIR}/meeting_sdk_demo.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingReminderEventListener.h
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingReminderEventListener.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingServiceEventListener.h
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingServiceEventListener.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/NetworkConnectionHandler.h
              ${CMAKE_CURRENT_SOURCE_DIR}/NetworkConnectionHandler.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/AuthServiceEventListener.h
              ${CMAKE_CURRENT_SOURCE_DIR}/AuthServiceEventListener.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingParticipantsCtrlEventListener.h
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingParticipantsCtrlEventListener.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingRecordingCtrlEventListener.h
              ${CMAKE_CURRENT_SOURCE_DIR}/MeetingRecordingCtrlEventListener.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKRenderer.h
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKRenderer.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKAudioRawData.h
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKAudioRawData.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKVideoSource.h
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKVideoSource.cpp
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKVirtualAudioMicEvent.h
              ${CMAKE_CURRENT_SOURCE_DIR}/ZoomSDKVirtualAudioMicEvent.cpp
              )

target_link_libraries(meetingSDKDemo gcc_s gcc)
target_link_libraries(meetingSDKDemo meetingsdk)
target_link_libraries(meetingSDKDemo glib-2.0)
target_link_libraries(meetingSDKDemo curl)
target_link_libraries(meetingSDKDemo pthread)


# Create a symbolic link
execute_process(COMMAND ln -s libmeetingsdk.so libmeetingsdk.so.1
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib/zoom_meeting_sdk
)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.txt ${CMAKE_CURRENT_SOURCE_DIR}/bin/config.txt COPYONLY)

file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/lib/zoom_meeting_sdk/ DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/bin)
