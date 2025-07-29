import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Modal,
  StyleSheet,
  Linking,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';

interface FootnoteLink {
  footnote_number: number;
  url: string;
  title: string;
  score: number;
  comments: number;
  subreddit: string;
  author: string;
  created_utc: string;
}

interface ReportRendererProps {
  fullReport: string;
  reportLinks?: FootnoteLink[];
  onClose?: () => void;
}

export default function ReportRenderer({ fullReport, reportLinks = [], onClose }: ReportRendererProps) {
  const [selectedFootnote, setSelectedFootnote] = useState<FootnoteLink | null>(null);
  const [modalVisible, setModalVisible] = useState(false);

  // 각주 번호를 클릭 가능한 컴포넌트로 변환
  const renderTextWithFootnotes = (text: string) => {
    const footnotePattern = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = footnotePattern.exec(text)) !== null) {
      // 각주 이전 텍스트
      if (match.index > lastIndex) {
        parts.push(
          <Text key={`text-${lastIndex}`}>
            {text.substring(lastIndex, match.index)}
          </Text>
        );
      }

      // 각주 번호
      const footnoteNumber = parseInt(match[1]);
      const footnoteLink = reportLinks.find(link => link.footnote_number === footnoteNumber);
      
      parts.push(
        <TouchableOpacity
          key={`footnote-${match.index}`}
          onPress={() => handleFootnotePress(footnoteLink)}
          style={styles.footnoteButton}
        >
          <Text style={styles.footnoteText}>{match[0]}</Text>
        </TouchableOpacity>
      );

      lastIndex = match.index + match[0].length;
    }

    // 마지막 텍스트
    if (lastIndex < text.length) {
      parts.push(
        <Text key={`text-${lastIndex}`}>
          {text.substring(lastIndex)}
        </Text>
      );
    }

    return parts;
  };

  const handleFootnotePress = (footnoteLink: FootnoteLink | undefined) => {
    if (footnoteLink) {
      setSelectedFootnote(footnoteLink);
      setModalVisible(true);
    }
  };

  const handleOpenLink = () => {
    if (selectedFootnote?.url) {
      Linking.openURL(selectedFootnote.url);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 보고서를 섹션별로 렌더링
  const renderReport = () => {
    const sections = fullReport.split('\n\n');
    return sections.map((section, index) => {
      if (section.startsWith('##')) {
        const title = section.substring(2).trim();
        return (
          <View key={`section-${index}`} style={styles.section}>
            <Text style={styles.sectionTitle}>{title}</Text>
          </View>
        );
      } else if (section.startsWith('**') && section.endsWith('**')) {
        return (
          <View key={`subsection-${index}`} style={styles.subsection}>
            <Text style={styles.subsectionTitle}>
              {section.replace(/\*\*/g, '')}
            </Text>
          </View>
        );
      } else if (section.trim()) {
        return (
          <View key={`paragraph-${index}`} style={styles.paragraph}>
            <Text style={styles.paragraphText}>
              {renderTextWithFootnotes(section)}
            </Text>
          </View>
        );
      }
      return null;
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {renderReport()}
        </View>
      </ScrollView>

      {/* 각주 상세 정보 모달 */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {selectedFootnote && (
              <>
                <View style={styles.modalHeader}>
                  <Text style={styles.modalTitle}>참조 [{selectedFootnote.footnote_number}]</Text>
                  <TouchableOpacity
                    onPress={() => setModalVisible(false)}
                    style={styles.closeButton}
                  >
                    <Text style={styles.closeButtonText}>✕</Text>
                  </TouchableOpacity>
                </View>

                <ScrollView style={styles.modalBody}>
                  <Text style={styles.postTitle}>{selectedFootnote.title}</Text>
                  
                  <View style={styles.postMeta}>
                    <Text style={styles.metaText}>
                      r/{selectedFootnote.subreddit} • u/{selectedFootnote.author}
                    </Text>
                    <Text style={styles.metaText}>
                      {formatDate(selectedFootnote.created_utc)}
                    </Text>
                  </View>

                  <View style={styles.postStats}>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{selectedFootnote.score}</Text>
                      <Text style={styles.statLabel}>점수</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{selectedFootnote.comments}</Text>
                      <Text style={styles.statLabel}>댓글</Text>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={styles.openLinkButton}
                    onPress={handleOpenLink}
                  >
                    <Text style={styles.openLinkButtonText}>원본 게시물 보기</Text>
                  </TouchableOpacity>
                </ScrollView>
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 12,
  },
  subsection: {
    marginBottom: 16,
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1C1C1E',
    marginBottom: 8,
  },
  paragraph: {
    marginBottom: 16,
  },
  paragraphText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#3C3C43',
  },
  footnoteButton: {
    marginHorizontal: 2,
  },
  footnoteText: {
    color: '#007AFF',
    fontSize: 15,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 34, // Safe area bottom
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1C1E',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 24,
    color: '#8E8E93',
  },
  modalBody: {
    padding: 20,
  },
  postTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#1C1C1E',
    marginBottom: 12,
    lineHeight: 22,
  },
  postMeta: {
    marginBottom: 16,
  },
  metaText: {
    fontSize: 13,
    color: '#8E8E93',
    marginBottom: 4,
  },
  postStats: {
    flexDirection: 'row',
    marginBottom: 20,
    paddingVertical: 16,
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
    color: '#8E8E93',
  },
  openLinkButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  openLinkButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});