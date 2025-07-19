import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  StyleSheet,
  Animated,
  TouchableWithoutFeedback,
  Dimensions,
} from 'react-native';

interface MenuItem {
  label: string;
  onPress: () => void;
  icon?: string;
  color?: string;
}

interface DropdownMenuProps {
  items: MenuItem[];
  trigger: React.ReactNode;
}

const DropdownMenu: React.FC<DropdownMenuProps> = ({ items, trigger }) => {
  const [visible, setVisible] = useState(false);
  const [buttonLayout, setButtonLayout] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const animation = useRef(new Animated.Value(0)).current;
  const buttonRef = useRef<TouchableOpacity>(null);

  useEffect(() => {
    if (visible) {
      Animated.timing(animation, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(animation, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }).start();
    }
  }, [visible, animation]);

  const measureButton = () => {
    buttonRef.current?.measure((x, y, width, height, pageX, pageY) => {
      setButtonLayout({ x: pageX, y: pageY, width, height });
      setVisible(true);
    });
  };

  const handleItemPress = (item: MenuItem) => {
    setVisible(false);
    setTimeout(() => {
      item.onPress();
    }, 150);
  };

  const menuStyle = {
    position: 'absolute' as const,
    top: buttonLayout.y + buttonLayout.height + 8,
    right: Dimensions.get('window').width - buttonLayout.x - buttonLayout.width,
    opacity: animation,
    transform: [
      {
        scale: animation.interpolate({
          inputRange: [0, 1],
          outputRange: [0.8, 1],
        }),
      },
    ],
  };

  return (
    <>
      <TouchableOpacity ref={buttonRef} onPress={measureButton}>
        {trigger}
      </TouchableOpacity>

      <Modal
        visible={visible}
        transparent
        animationType="none"
        onRequestClose={() => setVisible(false)}
      >
        <TouchableWithoutFeedback onPress={() => setVisible(false)}>
          <View style={styles.overlay}>
            <Animated.View style={[styles.menu, menuStyle]}>
              {items.map((item, index) => (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.menuItem,
                    index === items.length - 1 && styles.lastMenuItem,
                  ]}
                  onPress={() => handleItemPress(item)}
                >
                  {item.icon && (
                    <Text style={styles.menuItemIcon}>{item.icon}</Text>
                  )}
                  <Text
                    style={[
                      styles.menuItemText,
                      item.color && { color: item.color },
                    ]}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </Animated.View>
          </View>
        </TouchableWithoutFeedback>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
  },
  menu: {
    backgroundColor: '#1A1A1A',
    borderRadius: 12,
    minWidth: 180,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  lastMenuItem: {
    borderBottomWidth: 0,
  },
  menuItemIcon: {
    fontSize: 18,
    marginRight: 12,
  },
  menuItemText: {
    fontSize: 16,
    color: '#FFFFFF',
  },
});

export default DropdownMenu;